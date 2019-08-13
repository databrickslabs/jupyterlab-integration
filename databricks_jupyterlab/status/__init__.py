import json
import os
import subprocess
import threading
import time
from notebook.base.handlers import IPythonHandler
from tornado import web
from collections import defaultdict

import databricks_jupyterlab
from databricks_jupyterlab.remote import (get_db_config, is_reachable, get_cluster, prepare_ssh_config, is_reachable,
                                          check_installed, install_libs, connect)


class KernelHandler(IPythonHandler):
    NBAPP = None

    def get_kernel(self, kernel_id):
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
    @web.authenticated
    def get(self):
        profile = self.get_argument('profile', None, True)
        cluster_id = self.get_argument('cluster_id', None, True)
        kernel_id = self.get_argument('id', None, True)

        status = "Connected"

        kernel = self.get_kernel(kernel_id)
        if kernel is not None:
            if kernel.is_alive():
                status = "Connected"
            else:
                status = "DISCONNECTED"

        status_file = os.path.expanduser("~/.databricks-jupyterlab/%s_%s.starting" % (profile, cluster_id))
        status_file_exists = os.path.exists(status_file)
        if status_file_exists:
            try:
                with open(os.path.expanduser(status_file)) as fd:
                    status = fd.read()
            except:
                print("Warning: could not read %s" % status_file)
                status = "Unknown"

        result = {'status': "%s" % status}
        self.write(json.dumps(result))


class DbStartHandler(KernelHandler):
    @web.authenticated
    def get(self):
        profile = self.get_argument('profile', None, True)
        cluster_id = self.get_argument('cluster_id', None, True)
        kernel_id = self.get_argument('id', None, True)
        tf = threading.Thread(target=self.start_cluster, args=(profile, cluster_id, kernel_id))
        tf.start()

        result = {'status': "ok"}
        self.write(json.dumps(result))

    def start_cluster(self, profile, cluster_id, kernel_id):
        host, token = get_db_config(profile)
        apiclient = connect(profile)
        cluster_id, public_ip, cluster_name, started, status_file = get_cluster(apiclient, profile, host, token, cluster_id)

        status_file.log_ssh()
        prepare_ssh_config(cluster_id, profile, public_ip)
        if not is_reachable(public_dns=public_ip):
            status_file.log_error("ERROR: Cannot Connect to %s:%s" % (profile, cluster_id))
        else:
            status_file.log_check()
            if not check_installed(cluster_id):
                packages = json.loads(subprocess.check_output(["conda", "list", "--json"]))
                deps = {p["name"]: p["version"] for p in packages if p["name"] in ["ipywidgets", "sidecar"]}

                status_file.log_install_driver()
                module_path = os.path.dirname(databricks_jupyterlab.__file__)
                install_libs(cluster_id,
                             module_path,
                             ipywidets_version=deps["ipywidgets"],
                             sidecar_version=deps["sidecar"])
            
            kernel = self.get_kernel(kernel_id)
            
            status_file.log_done()
            time.sleep(1)
            kernel.restart_kernel()


def _jupyter_server_extension_paths():
    """
    Set up the server extension for collecting metrics
    """
    return [{
        'module': 'databricks_jupyterlab',
    }]


