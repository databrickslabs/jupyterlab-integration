from collections import defaultdict
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from notebook.base.handlers import IPythonHandler
from tornado import web
from collections import defaultdict
import ssh_config
from tornado.log import LogFormatter

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.remote import (connect, is_reachable, get_cluster, get_python_path, is_reachable,
                                              check_installed, install_libs, ssh)
from databrickslabs_jupyterlab.local import (get_db_config, prepare_ssh_config)
from databricks_cli.clusters.api import ClusterApi

_LOG_FMT = ("%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d "
            "%(name)s]%(end_color)s %(message)s")
_LOG_DATEFMT = "%H:%M:%S"

_console = logging.StreamHandler()
_console.setFormatter(LogFormatter(fmt=_LOG_FMT, datefmt=_LOG_DATEFMT))
_console.setLevel("INFO")

_logger = logging.getLogger("databrickslabs-jl")
_logger.propagate = False
_logger.setLevel("INFO")
_logger.handlers = []
_logger.addHandler(_console)

class SshConfig:
    class __SshConfig:
        def __init__(self):
            self.config_file = os.path.expanduser("~/.ssh/config")
            self.load()

        def _get_mtime(self):
            return os.stat(self.config_file).st_mtime

        def load(self):
            _logger.info("Loading ssh config")
            self.mtime = self._get_mtime()
            sc = ssh_config.SSHConfig.load(self.config_file)
            self.hosts = {
                h.name: h.attributes()["HostName"]
                for h in sc.hosts() if h.attributes().get("HostName", None) is not None
            }

        def get_dns(self, host_name):
            if self._get_mtime() > self.mtime:
                self.load()
            return self.hosts.get(host_name, None)

    instance = None

    def __init__(self):
        """Singleton initializer"""
        if not SshConfig.instance:
            SshConfig.instance = SshConfig.__SshConfig()

    def __getattr__(self, name):
        """Singleton getattr overload"""
        return getattr(self.instance, name)


class Status:
    """Singleton for the Status object"""
    class __Status:
        """Status implementation"""
        def __init__(self):
            self.status = defaultdict(lambda: {})
            self.dots = 0
            self.installing = {}

        def get_status(self, profile, cluster_id):
            """Get current cluster start status for the jupyterlab status line
            
            Args:
                profile (str): Databricks CLI profile string
                cluster_id (str): Cluster ID
            
            Returns:
                str: Cluster status or "unknown"
            """
            # print("get_status", profile, cluster_id, self.status[profile].get(cluster_id, None))
            if self.status.get(profile, None) is not None:
                status = self.status[profile].get(cluster_id, None)
                if status is None:
                    status = "unknown"
                return status
            else:
                return None

        def set_status(self, profile, cluster_id, status, new_status=True):
            """Set Cluster start status for the jupyterlab status line
            
            Args:
                profile (str): Databricks CLI profile string
                cluster_id (str): Cluster ID
                status (str): Status value
                new_status (bool, optional): If True, number of progress dots is set to 0. Defaults to True.
            """
            # print("set_status", profile, cluster_id, status, new_status)
            if new_status:
                self.dots = 0
            else:
                self.dots = (self.dots + 1) % 6
            # if status == "Connected":
            #     self.dots = 0
            self.status[profile][cluster_id] = status + ("." * self.dots)

        def get_installing(self, profile, cluster_id):
            return self.installing["%s %s" % (profile, cluster_id)]

        def set_installing(self, profile, cluster_id):
            self.installing["%s %s" % (profile, cluster_id)] = True

        def unset_installing(self, profile, cluster_id):
            self.installing["%s %s" % (profile, cluster_id)] = False

    instance = None

    def __init__(self):
        """Singleton initializer"""
        if not Status.instance:
            Status.instance = Status.__Status()

    def __getattr__(self, name):
        """Singleton getattr overload"""
        return getattr(self.instance, name)


class KernelHandler(IPythonHandler):
    """Kernel handler to get jupyter kernel for given kernelspec"""
    NBAPP = None

    def get_kernel(self, kernel_id):
        """Get jupyter kernel for given kernel Id
        
        Args:
            kernel_id (str): Internal jupyter kernel ID
        
        Returns:
            KernelManager: KernelManager object
        """
        km = KernelHandler.NBAPP.kernel_manager

        kernel_info = None
        for kernel_info in km.list_kernels():
            if kernel_info["id"] == kernel_id:
                break

        if kernel_info is not None:
            return km.get_kernel(kernel_info["id"])
        else:
            return None


class DbStatusHandler(KernelHandler):
    """Databricks cluster status handler"""
    @web.authenticated
    def get(self):
        """GET handler to return the current Databricks cluster start status"""
        profile = self.get_argument('profile', None, True)
        cluster_id = self.get_argument('cluster_id', None, True)
        # kernel_id = self.get_argument('id', None, True)

        # For the first run start_status is None.
        # Use REST API to provide a reasonable status
        status = None
        reachable = None
        state = None
        start_status = Status().get_status(profile, cluster_id)
        if start_status is None:
            Status().unset_installing(profile, cluster_id)
            state = self.get_cluster_state(profile, cluster_id)
            if state in ["PENDING", "RESTARTING"]:
                Status().set_installing(profile, cluster_id)
                start_status = "Pending"
            elif state in ["RUNNING", "RESIZING"]:
                start_status = "Running"
            elif state in ["TERMINATING", "TERMINATED"]:
                start_status = "TERMINATED"
            else:
                Status().unset_installing(profile, cluster_id)
                start_status = state  # ERROR, UNKNOWN

            Status().set_status(profile, cluster_id, start_status)

        if Status().get_installing(profile, cluster_id):
            # While the DbStartHandler is installing the kernel, provide its status
            status = start_status
        else:
            # Else, chekc reachability
            dns = SshConfig().get_dns(cluster_id)
            if dns is None:
                status = "ERROR: Unknown cluster id"
            else:
                reachable = is_reachable(dns)
                if reachable:
                    _logger.info("DbStatusHandler reachable = %s" % reachable)
                else:
                    _logger.warning("DbStatusHandler reachable = %s" % reachable)
                if reachable:
                    if start_status.lower() == "running":
                        status = "Connected"
                    elif start_status != "Connected":
                        state = self.get_cluster_state(profile, cluster_id)
                        status = state
                        if status == "RUNNING" and not self.check_ipykernel(cluster_id):
                            status =" ERROR: ipykernel not installed"
                else:
                    status = "UNREACHABLE"
                    if start_status == "TERMINATED":
                        status = "TERMINATED"
                    else:
                        if state is None:
                            state = self.get_cluster_state(profile, cluster_id)
                        if state == "TERMINATED":
                            status = state
                            Status().set_status(profile, cluster_id, status)

        result = {'status': "%s" % status}
        if status != "Connected":
            _logger.debug("DbStatusHandler: installing: '%s'; reachable: '%s'; state: '%s'; start_status: '%s'; status: '%s'" %
                (Status().installing, reachable, state, start_status, result))
        self.finish(json.dumps(result))

    def get_cluster_state(self, profile, cluster_id):
        apiclient = connect(profile)
        client = ClusterApi(apiclient)
        cluster = client.get_cluster(cluster_id)
        state = cluster.get("state", None)
        if state == "TERMINATED":
            _logger.warning("DbStatusHandler cluster state = %s" % state)
        else:
            _logger.info("DbStatusHandler cluster state = %s" % state)
        return state

    def check_ipykernel(self, cluster_id):
        python_path = get_python_path(cluster_id)
        lib = ssh(cluster_id, "%s show ipykernel" % python_path).strip()
        return len(lib) > 0

class DbStartHandler(KernelHandler):
    """Databricks cluster start handler"""
    @web.authenticated
    def get(self):
        """GET handler to trigger cluster start in a separate thread"""
        profile = self.get_argument('profile', None, True)
        cluster_id = self.get_argument('cluster_id', None, True)
        kernel_id = self.get_argument('id', None, True)
        thread = threading.Thread(target=self.start_cluster, args=(profile, cluster_id, kernel_id))
        thread.daemon = True
        thread.start()

        result = {'status': "ok"}
        self.finish(json.dumps(result))

    def start_cluster(self, profile, cluster_id, kernel_id):
        """Start cluster in a separate thread
        
        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
            kernel_id (str): Internal jupyter kernel ID
        """
        if Status().get_installing(profile, cluster_id):
            _logger.info("DbStartHandler cluster %s:%s already starting" % (profile, cluster_id))
        else:
            _logger.info("DbStartHandler cluster %s:%s start triggered" % (profile, cluster_id))
            Status().set_installing(profile, cluster_id)
            Status().set_status(profile, cluster_id, "Starting cluster")
            host, token = get_db_config(profile)
            cluster_id, public_ip, cluster_name, conda_env = get_cluster(profile, host, token, cluster_id, Status())
            if cluster_name is None:
                Status().set_status(profile, cluster_id, "ERROR: Cluster could not be found")
                return

            Status().set_status(profile, cluster_id, "Configuring SSH")
            prepare_ssh_config(cluster_id, profile, public_ip)
            if not is_reachable(public_dns=public_ip):
                Status().set_status(profile, cluster_id, "UNREACHABLE")
            else:
                python_path = get_python_path(cluster_id)

                Status().set_status(profile, cluster_id, "Checking driver libs")
                if not check_installed(cluster_id, python_path):
                    Status().set_status(profile, cluster_id, "Installing driver libs")
                    install_libs(cluster_id, python_path)

                # Recheck in case something went wrong
                if check_installed(cluster_id, python_path):
                    Status().set_status(profile, cluster_id, "Driver libs installed")
                else:
                    Status().set_status(profile, cluster_id, "ERROR: Driver libs not installed")
                    return

                time.sleep(2)
                kernel = self.get_kernel(kernel_id)
                kernel.restart_kernel(now=True)
                Status().set_status(profile, cluster_id, "Running")
            Status().unset_installing(profile, cluster_id)


def _jupyter_server_extension_paths():
    """
    Set up the server extension for status handling
    """
    return [{
        'module': 'databrickslabs_jupyterlab',
    }]
