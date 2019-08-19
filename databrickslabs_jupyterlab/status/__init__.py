from collections import defaultdict
import json
import os
import subprocess
import threading
import time
from notebook.base.handlers import IPythonHandler
from tornado import web
from collections import defaultdict

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.remote import (get_db_config, is_reachable, get_cluster, prepare_ssh_config, is_reachable,
                                          check_installed, install_libs)


class Status:
    """Singleton for the Status object"""

    class __Status:
        """Status implementation"""
        def __init__(self):
            self.status = defaultdict(lambda : {})
            self.dots = 0

        def get_status(self, profile, cluster_id):
            """Get current cluster start status for the jupyterlab status line
            
            Args:
                profile (str): Databricks CLI profile string
                cluster_id (str): Cluster ID
            
            Returns:
                str: Cluster status or "unknown"
            """
            # print("get_status", profile, cluster_id, self.status[profile].get(cluster_id, None))
            if self.status[profile] != {}:
                return self.status[profile][cluster_id]
            else:
                return "unknown"

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
            self.status[profile][cluster_id] = status + ("."*self.dots)

    instance = None
    def __init__(self):
        """Singleton initializer"""
        if not Status.instance:
            Status.instance = Status.__Status()

    def __getattr__(self, name):
        """Singleton getattr overload"""
        return getattr(self.instance, name)


class KernelHandler(IPythonHandler):
    """Kernel handler to get jupyter kernel for given ker"""
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
        kernel_id = self.get_argument('id', None, True)

        start_status = Status().get_status(profile, cluster_id)

        status = "unknown"
        if start_status == "Started":
            status = "Connected"
            Status().set_status(profile, cluster_id, status)
        else:
            kernel = self.get_kernel(kernel_id)
            if kernel is not None:
                if kernel.is_alive():
                    alive = "True"
                    status = "Connected"
                else:
                    alive = "False"
                    status = "TERMINATED"
                    if start_status in ["Connected", "unknown"]:
                        Status().set_status(profile, cluster_id, status)
                    else:
                        status = start_status

        result = {'status': "%s" % status}
        # print("start_status: '%s'; alive: '%s; status: '%s'" % (start_status, alive,result))
        self.finish(json.dumps(result))


class DbStartHandler(KernelHandler):
    """Databricks cluster start handler"""
    @web.authenticated
    def get(self):
        """GET handler to trigger cluster start in a separate thread"""
        profile = self.get_argument('profile', None, True)
        cluster_id = self.get_argument('cluster_id', None, True)
        kernel_id = self.get_argument('id', None, True)
        tf = threading.Thread(target=self.start_cluster, args=(profile, cluster_id, kernel_id))
        tf.start()

        result = {'status': "ok"}
        self.finish(json.dumps(result))

    def start_cluster(self, profile, cluster_id, kernel_id):
        """Start cluster in a separate thread
        
        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
            kernel_id (str): Internal jupyter kernel ID
        """
        Status().set_status(profile, cluster_id, "Starting cluster")
        host, token = get_db_config(profile)
        cluster_id, public_ip, cluster_name, started = get_cluster(profile, host, token, cluster_id, Status())

        Status().set_status(profile, cluster_id, "Configuring SSH")
        prepare_ssh_config(cluster_id, profile, public_ip)
        if not is_reachable(public_dns=public_ip):
            Status().set_status(profile, cluster_id, "UNREACHABLE")
        else:
            Status().set_status(profile, cluster_id, "Checking driver libs")
            if not check_installed(cluster_id):
                packages = json.loads(subprocess.check_output(["conda", "list", "--json"]))
                deps = {p["name"]: p["version"] for p in packages if p["name"] in ["ipywidgets", "sidecar"]}

                Status().set_status(profile, cluster_id, "Installing driver libs")
                module_path = os.path.dirname(databrickslabs_jupyterlab.__file__)
                install_libs(cluster_id,
                             module_path,
                             ipywidets_version=deps["ipywidgets"],
                             sidecar_version=deps["sidecar"])

            time.sleep(2)
            kernel = self.get_kernel(kernel_id)
            # kernel.shutdown_kernel(now=True)
            kernel.restart_kernel(now=True)
            Status().set_status(profile, cluster_id, "Started")


def _jupyter_server_extension_paths():
    """
    Set up the server extension for status handling
    """
    return [{
        'module': 'databrickslabs_jupyterlab',
    }]
