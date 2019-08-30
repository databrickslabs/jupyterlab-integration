from collections import defaultdict
import json
import logging
import os
import socket
import sys
import threading
import time
from notebook.base.handlers import IPythonHandler
from tornado import web
from collections import defaultdict
from tornado.log import LogFormatter

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.remote import (connect, is_reachable, get_cluster, get_python_path, check_installed,
                                              install_libs)
from databrickslabs_jupyterlab.utils import SshConfig
from databrickslabs_jupyterlab.local import (get_db_config, prepare_ssh_config)
from databricks_cli.clusters.api import ClusterApi

DEBUG_LEVEL = "INFO"

_LOG_FMT = ("%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d " "%(name)s]%(end_color)s %(message)s")
_LOG_DATEFMT = "%H:%M:%S"

_console = logging.StreamHandler()
_console.setFormatter(LogFormatter(fmt=_LOG_FMT, datefmt=_LOG_DATEFMT))
_console.setLevel(DEBUG_LEVEL)

_logger = logging.getLogger("databrickslabs-jl")
_logger.propagate = False
_logger.setLevel(DEBUG_LEVEL)
_logger.handlers = []
_logger.addHandler(_console)


def get_cluster_state(profile, cluster_id):
    """Get cluster state
    
    Args:
        profile (str): Databricks CLI profile string
        cluster_id (str): Cluster ID
    
    Returns:
        dict: ClusterStatus
    """
    apiclient = connect(profile)
    client = ClusterApi(apiclient)
    cluster = client.get_cluster(cluster_id)
    state = cluster.get("state", None)
    if state == "TERMINATED":
        _logger.warning("DbStatusHandler cluster state = %s" % state)
    else:
        _logger.info("DbStatusHandler cluster state = %s" % state)

    return state


class Status:
    """Status implementation"""
    def __init__(self):
        self.status = defaultdict(lambda: defaultdict(lambda: {}))
        self.dots = 0
        self._installing = defaultdict(lambda: None)

    def get_status(self, profile, cluster_id):
        """Get current cluster start status for the jupyterlab status line
        
        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
        
        Returns:
            str: Cluster status or "UNKNOWN"
        """
        if self.status[profile][cluster_id] == {}:
            # For the first run start_status is None.
            # Use REST API to provide a reasonable status
            state = get_cluster_state(profile, cluster_id)  # called max once
            if state in ["PENDING", "RESTARTING"]:
                status = "Pending"  # special status, don't set in global state
            elif state in ["RUNNING", "RESIZING"]:
                status = "Running"  # standard status
            elif state in ["TERMINATING", "TERMINATED"]:
                status = "UNREACHABLE"  # standard status
            else:
                status = state  # ERROR, UNKNOWN non standard status
            self.set_status(profile, cluster_id, status)

        return self.status[profile][cluster_id]

    def set_status(self, profile, cluster_id, status, new_status=True):
        """Set Cluster start status for the jupyterlab status line
        
        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
            status (str): Status value
            new_status (bool, optional): If True, number of progress dots is set to 0. Defaults to True.
        """
        self.dots = 0 if new_status else (self.dots + 1) % 6
        self.status[profile][cluster_id] = status + ("." * self.dots)

    def installing(self, profile, cluster_id):
        """Check whether cluster is currently in installation mode
        
        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
        
        Returns:
            bool: True if in installation mode, else False
        """
        return self._installing["%s %s" % (profile, cluster_id)]

    def set_installing(self, profile, cluster_id):
        """Set installation mode for a cluster
        
        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
        """
        self._installing["%s %s" % (profile, cluster_id)] = True

    def unset_installing(self, profile, cluster_id):
        """Unset installation mode for a cluster
        
        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
        """
        self._installing["%s %s" % (profile, cluster_id)] = False


class KernelHandler(IPythonHandler):
    """Kernel handler to get jupyter kernel for given kernelspec"""
    nbapp = None
    status = Status()

    def get_kernel(self, kernel_id):
        """Get jupyter kernel for given kernel Id
        
        Args:
            kernel_id (str): Internal jupyter kernel ID
        
        Returns:
            KernelManager: KernelManager object
        """
        km = KernelHandler.nbapp.kernel_manager

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
        global_status = KernelHandler.status

        profile = self.get_argument('profile', None, True)
        cluster_id = self.get_argument('cluster_id', None, True)
        kernel_id = self.get_argument('id', None, True)

        status = None
        reachable = None
        start_status = global_status.get_status(profile, cluster_id)
        # returns Running, Pending, ERROR, UNKNOWN from remote
        # and a chain of staus ending with "Running" if DbStartHandler started cluster

        if global_status.installing(profile, cluster_id):
            # While the DbStartHandler is installing the kernel, provide the global starting status
            status = start_status
        else:
            # Else, check reachability
            dns = SshConfig().get_dns(cluster_id)
            if dns is None:
                status = "ERROR: Unknown cluster id"
            else:
                reachable = is_reachable(dns)  # fairly cheap, opens a socket and closes it
                if reachable:
                    if start_status == "Running":
                        # global start status "Running" is mapped to UI status "Connected"
                        status = "Connected"
                    else:
                        status = start_status

                    # Even when reachable, libraries can be missing
                    kernel = self.get_kernel(kernel_id)
                    if kernel is not None:
                        alive = kernel.is_alive()
                        if not alive:
                            _logger.error("DbStatusHandler: kernel is dead (start_status=%s)" % start_status)
                            # checking against "MISSING LIBS" ensures check_installed will only be called once
                            host, token = get_db_config(profile)
                            if start_status != "MISSING LIBS" and not check_installed(cluster_id, host, token):
                                _logger.error("DbStatusHandler: libraries are missing on remote server")
                                status = "MISSING LIBS"
                                global_status.set_status(profile, cluster_id, status)
                else:
                    _logger.warning("DbStatusHandler: kernel is not reachable")
                    status = "UNREACHABLE"

        result = {'status': "%s" % status}
        _logger.debug("DbStatusHandler: installing: '%s'; reachable: '%s'; start_status: '%s'; ; status: '%s'" %
            (global_status.installing(profile, cluster_id), reachable, start_status, result))
        self.finish(json.dumps(result))


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
        global_status = KernelHandler.status

        if global_status.installing(profile, cluster_id):
            _logger.info("DbStartHandler cluster %s:%s already starting" % (profile, cluster_id))
        else:
            _logger.info("DbStartHandler cluster %s:%s start triggered" % (profile, cluster_id))
            global_status.set_installing(profile, cluster_id)

            host, token = get_db_config(profile)
            cluster_id, public_ip, cluster_name, dummy = get_cluster(profile, host, token, cluster_id, global_status)
            if cluster_name is None:
                global_status.set_status(profile, cluster_id, "ERROR: Cluster could not be found")
                return

            global_status.set_status(profile, cluster_id, "Configuring SSH")
            prepare_ssh_config(cluster_id, profile, public_ip)
            if not is_reachable(public_dns=public_ip):
                global_status.set_status(profile, cluster_id, "UNREACHABLE")
            else:
                global_status.set_status(profile, cluster_id, "Installing driver libs")
                result = install_libs(cluster_id, host, token)
                if result[0] == 0:
                    _logger.info("DbStartHandler: installations done")
                else:
                    _logger.error("DbStartHandler: installations failed")
                    global_status.set_status(profile, cluster_id, "ERROR")

                time.sleep(1)
                kernel = self.get_kernel(kernel_id)
                kernel.restart_kernel(now=True)
                global_status.set_status(profile, cluster_id, "Running")
            global_status.unset_installing(profile, cluster_id)


def _jupyter_server_extension_paths():
    """
    Set up the server extension for status handling
    """
    return [{
        'module': 'databrickslabs_jupyterlab',
    }]
