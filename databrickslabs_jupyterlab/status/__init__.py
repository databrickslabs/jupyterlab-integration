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
from tornado.log import LogFormatter

from databricks_cli.clusters.api import ClusterApi

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.remote import (
    connect,
    is_reachable,
    get_cluster,
    get_python_path,
    check_installed,
    install_libs,
)

from databrickslabs_jupyterlab.kernel import DatabricksKernelStatus
from databrickslabs_jupyterlab.utils import SshConfig
from databrickslabs_jupyterlab.local import get_db_config, prepare_ssh_config

DEBUG_LEVEL = os.environ.get("DEBUG_STATUS", "INFO")

_LOG_FMT = (
    "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d " "%(name)s]%(end_color)s %(message)s"
)
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
    try:
        client = ClusterApi(apiclient)
        cluster = client.get_cluster(cluster_id)
        state = cluster.get("state", None)
    except:  # pylint: disable=bare-except
        _logger.warning("DbStatusHandler cluster not reachable")
        state = "TERMINATED"
    # if state == "TERMINATED":
    #     _logger.warning("DbStatusHandler cluster state = %s" % state)
    # else:
    #     _logger.info("DbStatusHandler cluster state = %s" % state)

    return state


class Status:
    """Status implementation"""

    def __init__(self):
        self.status = defaultdict(lambda: defaultdict(lambda: {}))
        self.dots = 0
        self._installing = defaultdict(lambda: None)
        self._ignore_next_unreachable = False

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
                status = "Starting"  # special status, don't set in global state
            elif state in ["RUNNING", "RESIZING"]:
                status = "Connected"  # standard status
            elif state in ["TERMINATING", "TERMINATED"]:
                status = "UNREACHABLE"  # standard status
            else:
                status = state  # ERROR, UNKNOWN non standard status
            self.set_status(profile, cluster_id, status)

        return self.status[profile][cluster_id]

    def reset_status(self, profile, cluster_id):
        self.status[profile][cluster_id] = {}

    def set_status(self, profile, cluster_id, status, new_status=True):
        """Set Cluster start status for the jupyterlab status line

        Args:
            profile (str): Databricks CLI profile string
            cluster_id (str): Cluster ID
            status (str): Status value
            new_status (bool, optional): If True, number of progress dots is set to 0.
                                         Defaults to True.
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
        self._ignore_next_unreachable = True

    def ignore_next_unreachable(self):
        result = self._ignore_next_unreachable
        self._ignore_next_unreachable = False
        return result


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

    def data_received(self, chunk):
        pass


class DbStatusHandler(KernelHandler):
    """Databricks cluster status handler"""

    @web.authenticated
    def get(self):
        """GET handler to return the current Databricks cluster start status"""
        global_status = KernelHandler.status

        profile = self.get_argument("profile", None, True)
        cluster_id = self.get_argument("cluster_id", None, True)
        kernel_id = self.get_argument("id", None, True)

        kernel = self.get_kernel(kernel_id)
        if kernel is None:
            status = "KERNEL_KILLED"
            start_status = "KERNEL_KILLED"
            status_message = "Kernel killed"
        else:
            conn_info = {
                "control_port": kernel.control_port,
                "hb_port": kernel.hb_port,
                "iopub_port": kernel.iopub_port,
                "shell_port": kernel.shell_port,
                "stdin_port": kernel.stdin_port,
            }
            kernel_status = DatabricksKernelStatus(conn_info, _logger)

            status = None
            start_status = global_status.get_status(profile, cluster_id)

            if global_status.installing(profile, cluster_id):
                # While the DbStartHandler is installing the kernel, provide the
                # global starting status
                status = start_status
            else:

                if kernel_status.is_running():
                    status = "Running"
                elif kernel_status.is_spark_running():
                    status = "Running (Spark)"
                elif kernel_status.is_starting():
                    status = "Starting"
                elif kernel_status.is_unknown():
                    # Use REST API to determine status
                    global_status.reset_status(profile, cluster_id)
                    status = global_status.get_status(profile, cluster_id)
                elif kernel_status.is_connect_failed():
                    status = "CONNECT FAILED"
                else:
                    # just swallow the intermediate UNREACHABLE after a restart
                    if global_status.ignore_next_unreachable():
                        status = "Starting"
                    else:
                        status = "UNREACHABLE"
            status_message = kernel_status.get_status_message()

        result = {"status": "%s" % status}
        _logger.debug(
            "DbStatusHandler: installing: '%s'; start_status: '%s'; kernel_status: '%s'; status: '%s'",
            global_status.installing(profile, cluster_id),
            start_status,
            status_message,
            result,
        )
        self.finish(json.dumps(result))


class DbStartHandler(KernelHandler):
    """Databricks cluster start handler"""

    @web.authenticated
    def get(self):
        """GET handler to trigger cluster start in a separate thread"""
        profile = self.get_argument("profile", None, True)
        cluster_id = self.get_argument("cluster_id", None, True)
        kernel_id = self.get_argument("id", None, True)
        thread = threading.Thread(target=self.start_cluster, args=(profile, cluster_id, kernel_id))
        thread.daemon = True
        thread.start()

        result = {"status": "ok"}
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
            _logger.info("DbStartHandler cluster %s:%s already starting", profile, cluster_id)
        else:
            _logger.info("DbStartHandler cluster %s:%s start triggered", profile, cluster_id)
            global_status.set_installing(profile, cluster_id)

            host, token = get_db_config(profile)
            cluster_id, endpoint, cluster_name, dummy = get_cluster(
                profile, cluster_id, global_status
            )
            if cluster_name is None:
                global_status.set_status(profile, cluster_id, "ERROR: Cluster could not be found")
                return

            global_status.set_status(profile, cluster_id, "Configuring SSH")
            prepare_ssh_config(cluster_id, profile, endpoint)
            if not is_reachable(endpoint):
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
    return [
        {
            "module": "databrickslabs_jupyterlab",
        }
    ]
