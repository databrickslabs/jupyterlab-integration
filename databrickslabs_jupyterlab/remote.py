import base64
import json
import os
import re
import sys
import time
from os.path import expanduser
import socket
import subprocess
import uuid
import glob

import inquirer
import requests
from urllib.parse import unquote

from databricks_cli.configure.provider import get_config, ProfileConfigProvider
from databricks_cli.sdk.api_client import ApiClient
from databricks_cli.clusters.api import ClusterApi
from databricks_cli.libraries.api import LibrariesApi

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab._version import __version__
from databrickslabs_jupyterlab.rest import Command, DatabricksApiException
from databrickslabs_jupyterlab.utils import bye, Dark, print_ok, print_error, print_warning
from databrickslabs_jupyterlab.local import execute, get_local_libs, utf8_decode


def connect(profile):
    """Initialize Databricks API client
    
    Args:
        profile (str): Databricks CLI profile string
    
    Returns:
        ApiClient: Databricks ApiClient object
    """
    config = ProfileConfigProvider(profile).get_config()
    if config is None:
        print_error("Cannot initialize ApiClient")
        bye(1)
    verify = config.insecure is None
    if config.is_valid_with_token:
        return ApiClient(host=config.host, token=config.token, verify=verify)
    else:
        print_error("Token for profile '%s' is invalid" % profile)
        bye(1)


def select_cluster(clusters):
    """Build a list of clusters for the user to select one
    
    Args:
        clusters (list): list of clusters
    
    Returns:
        dict: Cluster config of selected cluster
    """
    def entry(i, cluster):
        if cluster.get("autoscale", None) is None:
            return "%s: '%s' (id: %s, state: %s, workers: %d)" % (i, cluster["cluster_name"], cluster["cluster_id"],
                                                                cluster["state"], cluster["num_workers"])
        else:
            return "%s: '%s' (id: %s, state: %s, scale: %d-%d)" % (i, cluster["cluster_name"], cluster["cluster_id"],
                                                                 cluster["state"], cluster["autoscale"]["min_workers"],
                                                                 cluster["autoscale"]["max_workers"])

    choice = [
        inquirer.List('cluster_id',
                      message='Which cluster to connect to?',
                      choices=[entry(i, cluster) for i, cluster in enumerate(clusters)])
    ]
    answer = inquirer.prompt(choice, theme=Dark())
    return clusters[int(answer["cluster_id"].split(":")[0])]


def get_cluster(profile, host, token, cluster_id=None, status=None):
    """Get the cluster configuration from remote
    
    Args:
        profile (str): Databricks CLI profile string
        host (str): host from databricks cli config for given profile string
        token (str): token from databricks cli config for given profile stringf
        cluster_id (str, optional): If cluster_id is given, the user will not be asked to select one. Defaults to None.
        status (Status, optional): A Status class providing set_status. Defaults to None.
    
    Returns:
        tuple: Cluster configs: cluster_id, public_ip, cluster_name and a flag whether it was started
    
    Returns:
        tuple: (cluster_id, public_ip, cluster_name, started)
    """
    with open("%s/.ssh/id_%s.pub" % (expanduser("~"), profile)) as fd:
        try:
            ssh_pub = fd.read().strip()
        except:
            print_error("   Error: ssh key for profile 'id_%s.pub' does not exist in %s/.ssh" % (profile, expanduser("~")))
            bye()

    try:
        apiclient = connect(profile)
        client = ClusterApi(apiclient)
        clusters = client.list_clusters()
    except Exception as ex:
        print_error(ex)
        return (None, None, None, None)

    clusters = clusters["clusters"]

    if cluster_id is not None:
        cluster = None
        for c in clusters:
            if c["cluster_id"] == cluster_id:
                cluster = c
                break

        if cluster is None:
            print_error("   Error: A cluster with id '%s' does not exist in the workspace of profile '%s'" %
                        (cluster_id, profile))
            return (None, None, None, None)

        if ssh_pub not in [c.strip() for c in cluster.get("ssh_public_keys", [])]:
            print_error("   Error: Cluster with id '%s' does not have ssh key '~/.ssh/id_%s' configured" %
                        (cluster_id, profile))
            return (None, None, None, None)
    else:
        my_clusters = [
            cluster for cluster in clusters
            if ssh_pub in [c.strip() for c in cluster.get("ssh_public_keys", [])]
        ]

        if not my_clusters:
            print_error(
                "    Error: There is no cluster in the workspace for profile '%s' configured with ssh key '~/.ssh/id_%s':" %
                (profile, profile))
            print("    Use 'databrickslabs_jupyterlab %s -s' to configure ssh for clusters in this workspace\n" % profile)
            return (None, None, None, None)

        current_conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
        found = None
        for i, c in enumerate(my_clusters):
            if c["cluster_name"].replace(" ", "_") == current_conda_env:
                found = c["cluster_name"]
                break

        if found is not None:
            print_warning(
                "\n   => The current conda environment is '%s'.\n      You might want to select cluster %d with the name '%s'?\n" %
                (current_conda_env, i, found))

        cluster = select_cluster(my_clusters)

    cluster_id = cluster["cluster_id"]
    cluster_name = cluster["cluster_name"]

    try:
        response = client.get_cluster(cluster_id)
    except Exception as ex:
        print_error(ex)
        return (None, None, None, None)

    state = response["state"]
    if not state in ["RUNNING", "RESIZING"]:
        if state == "TERMINATED":
            print("   => Starting cluster %s" % cluster_id)
            if status is not None:
                status.set_status(profile, cluster_id, "Cluster Starting")
            try:
                response = client.start_cluster(cluster_id)
            except Exception as ex:
                print_error(ex)
                return (None, None, None, None)

        print("   => Waiting for cluster %s being started (this can take up to 5 min)" % cluster_id)
        print("   ", end="", flush=True)

        while not state in ("RUNNING", "RESIZING"):
            if status is not None:
                status.set_status(profile, cluster_id, "Cluster Starting", False)
            print(".", end="", flush=True)
            time.sleep(5)
            try:
                response = client.get_cluster(cluster_id)
            except Exception as ex:
                print_error(ex)
                return (None, None, None, None)

            if response.get("error", None) is not None:
                print_error(response["error"])
                return (None, None, None, None)
            else:
                state = response["state"]
        print_ok("\n   => OK")

        if status is not None:
            status.set_status(profile, cluster_id, "Cluster started")

        print("\n   => Waiting for libraries on cluster %s being installed (this can take some time)" % cluster_id)
        print("   ", end="", flush=True)

        done = False
        while not done:
            try:
                states = get_library_state(profile, cluster_id)
            except DatabricksApiException as ex:
                print_error(ex)
                return (None, None, None, None)
            installing = any([s in ["PENDING", "RESOLVING", "INSTALLING"] for s in states])
            if installing:
                if status is not None:
                    status.set_status(profile, cluster_id, "Installing cluster libraries", False)
                print(".", end="", flush=True)
                time.sleep(5)
            else:
                done = True
                print_ok("\n   => OK\n")

        if status is not None:
            status.set_status(profile, cluster_id, "Cluster libraries installed", False)

    public_ip = response["driver"].get("public_dns", None)
    if public_ip is None:
        print_error("   Error: Cluster does not have public DNS name")
        return (None, None, None, None)

    print_ok("   => Selected cluster: %s (%s)" % (cluster_name, public_ip))

    return (cluster_id, public_ip, cluster_name, None)


def get_python_path(host, conda_env=None):
    # conda_default_env = ssh(host, "echo $DEFAULT_DATABRICKS_ROOT_CONDA_ENV").strip().decode("utf-8")
    # if conda_default_env == "":
    #     python_path = "/databricks/python3/bin"
    #     print_ok("   => %s (pip managed cluster)" % python_path)
    # else:
    #     if conda_env is None:  # if there is no conda environment variable, use default
    #         conda_env = conda_default_env
    #     python_path = "/databricks/conda/envs/%s/bin" % conda_env
    #     print_ok("   => %s (conda managed cluster)" % python_path)

    python_path = "/databricks/python/bin"
    return python_path


def install_libs(cluster_id, host, token):
    """Install ipywidgets, sidecar and databrickslabs_jupyterlab libraries on the driver
    
    Args:
        host (str): host from databricks cli config for given profile string
        python_path (str): Remote python path to be used for kernel
    """
    python_path = get_python_path(cluster_id)

    packages = get_local_libs()
    deps = {p["name"]: p["version"] for p in packages if p["name"] in ["ipywidgets", "sidecar"]}
    libs = ["ipywidgets==%s" % deps["ipywidgets"],
            "sidecar==%s" % deps["sidecar"],
            "databrickslabs-jupyterlab==%s" % __version__]
    pip_cmd = ["%s/pip" %python_path,  "install", "-q", "--no-warn-conflicts", "--disable-pip-version-check"] + libs

    cmd =  'import subprocess, json; ' + \
          ('ret = subprocess.run(%s, stderr=subprocess.PIPE); ' % pip_cmd) + \
           'print(json.dumps([ret.returncode, str(ret.stderr)]))'

    print("   => Installing %s" % ", ".join(libs))
    print("   ", end="")
    try:
        command = Command(url=host, cluster_id=cluster_id, token=token)
        result = command.execute(cmd)
        command.close()
        print()
    except DatabricksApiException as ex:
        print("REST API error", ex)
        return False

    if result[0] == 0:
        return tuple(json.loads(utf8_decode(result[1])))
    else:
        return result


def get_remote_packages(cluster_id, host, token):
    cmd = 'import sys, pkg_resources, json; ' + \
          'print(json.dumps([{"name": "python", "version": "%d.%d" % (sys.version_info.major, sys.version_info.minor)}] + ' + \
          '[{"name":p.key, "version":p.version} for p in pkg_resources.working_set]))'
    try:
        command = Command(url=host, cluster_id=cluster_id, token=token)
        result = command.execute(cmd)
        command.close()
    except DatabricksApiException as ex:
        print(ex)
        return None
    return result

def is_reachable(public_dns):
    """Check whether a remote cluster is reachable
    
    Args:
        public_dns (str): Public IP address or DNS name
    
    Returns:
        bool: True if reachable else False
    """
    return subprocess.call(["nc", "-z", public_dns, "2200"]) == 0
    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.settimeout(3)
    # result = sock.connect_ex((public_dns, 2200))
    # try:
    #     sock.close()
    # except:
    #     pass
    # return result == 0


def get_library_state(profile, cluster_id):
    """Get the state of the library installation on the remote cluster
    
    Args:
        cluster_id (str): Cluster ID
        host (str): host from databricks cli config for given profile string
        token (str): token from databricks cli config for given profile stringf
    
    Returns:
        list: list of installation status for each custom library
    """
    try:
        apiclient = connect(profile)
        client = LibrariesApi(apiclient)
        libraries = client.cluster_status(cluster_id)
    except Exception as ex:
        print_error(ex)
        return None

    if libraries.get("library_statuses", None) is None:
        return []
    else:
        return [lib["status"] for lib in libraries["library_statuses"]]


def check_installed(cluster_id, host, token):
    """Check whether databrickslabs_jupyterlab is installed on the remote host
    
    Args:
    
    Returns:
        bool: True if installed else False
    """
    result = get_remote_packages(cluster_id, host, token)
    if result[0] == 0:
        packages = json.loads(result[1])
        package_names = [p["name"] for p in packages]
        needed = ["databrickslabs-jupyterlab", "ipywidgets", "ipykernel"]

        return all([p in package_names for p in needed])
    else:
        print(result[1])
        return False


def version_check(cluster_id, host, token, flag):
    """Compare local and remote library versions
    
    Args:
        cluster_id (str): Cluster ID
        host (str): host from databricks cli config for given profile string
        token (str): token from databricks cli config for given profile string
        flag (str): all|diff|same
    """
    def normalize(key):
        return key.lower().replace("-", "_")

    packages = get_local_libs()
    deps = {normalize(p["name"]): p["version"] for p in packages}

    result = get_remote_packages(cluster_id, host, token)
    if result[0] == 0:
        remote_packages = json.loads(result[1])
    else:
        return
    remote_deps = {normalize(p["name"]): p["version"] for p in remote_packages}
    joint_keys = sorted(list(set(list(deps.keys()) + list(remote_deps.keys()))))
    print("%-30s %-10s%-10s" % ("Package", "local", "remote"))
    if str(flag) == "all":
        scope = joint_keys
    elif str(flag) == "same":
        scope = [key for key in joint_keys if deps.get(key, None) == remote_deps.get(key, None)]
    else:
        scope = [
            key for key in joint_keys if deps.get(key, None) != remote_deps.get(key, None)
            #            and deps.get(key, None) is not None and remote_deps.get(key, None) is not None
        ]
    for key in scope:
        result = "%-30s %-10s  %-10s" % (key, deps.get(key, "--"), remote_deps.get(key, "--"))
        if deps.get(key) == remote_deps.get(key):
            print_ok(result)
        else:
            print_error(result)

def configure_ssh(profile, host, token, cluster_id):
    """Configure SSH for the remote cluster
    
    Args:
        profile (str): Databricks CLI profile string
        host (str): host from databricks cli config for given profile string
        token (str): token from databricks cli config for given profile string
        cluster_id (str): cluster ID
    """
    sshkey_file = os.path.expanduser("~/.ssh/id_%s" % profile)
    if not os.path.exists(sshkey_file):
        print("\n   => ssh key '%s' does not exist" % sshkey_file)
        answer = input("   => Shall it be created (y/n)? (default = n): ")
        if answer.lower() == "y":
            print("   => Creating ssh key %s" % sshkey_file)
            result = execute(["ssh-keygen", "-b", "2048",  "-N", "", "-f",  sshkey_file])
            if result["returncode"] == 0:
                print_ok("   => OK")
            else:
                print_error(result["stderr"])
                bye()
        else:
            bye()
    else:
        print_ok("\n   => ssh key '%s' already exists" % sshkey_file)

    with open(sshkey_file + ".pub", "r") as fd:
        sshkey = fd.read().strip()

    try:
        apiclient = connect(profile)
        client = ClusterApi(apiclient)
    except Exception as ex:
        print_error(ex)
        return None

    try:
        response = client.get_cluster(cluster_id)
    except Exception as ex:
        print_error(ex)
        return None

    ssh_public_keys = response.get("ssh_public_keys", [])
    if sshkey in [key.strip() for key in ssh_public_keys]:
        print_ok("   => public ssh key already configured for cluster %s" % cluster_id)
        bye()

    request = {}
    for key in [
            "autotermination_minutes", "cluster_id", "cluster_name", "cluster_source", "creator_user_name",
            "default_tags", "driver_node_type_id", "enable_elastic_disk", "init_scripts_safe_mode", "node_type_id",
            "spark_env_vars", "spark_version"
    ]:
        request[key] = response[key]

    if response.get("aws_attributes", None) is not None:
        request["aws_attributes"] = response["aws_attributes"]

    if response.get("num_workers", None) is not None:
        request["num_workers"] = response["num_workers"]

    if response.get("autoscale", None) is not None:
        request["autoscale"] = response["autoscale"]

    request["ssh_public_keys"] = ssh_public_keys + [sshkey]

    print_warning("   => The ssh key will be added to the cluster. \n   Note: The cluster will be restarted immediately!")
    answer = input("   => Shall the ssh key be added and the cluster be restarted (y/n)? (default = n): ")
    if answer.lower() == "y":
        try:
            response = client.edit_cluster(request)
        except DatabricksApiException as ex:
            print_error(str(ex))
            return None
        print_ok("   => OK")
    else:
        print_error("   => Cancelled")

def download_notebook(url):
    """Download Databricks demo notebooks from docs.databricks.com.
    It adds two cells on the top to initialize the Databricks context and MLflow
    
    Args:
        url (str): The HTML url copied from the "Get notebook link"
    """

    def wrap(typ, cell):
        return {"cell_type":typ, "source": cell, "output":[], "metadata":{}, "execution_count":0 }

    cell1 = """# Retrieve Spark Context
from databrickslabs_jupyterlab.connect import dbcontext, is_remote
dbcontext()"""

    cell2 = """# Setup MLflow (optional)
import os
from mlflow
from mlflow.tracking import MlflowClient

def remote_mlflow_setup(experiment_name):
    mlflow.set_experiment(experiment_name)
    experiment = MlflowClient().get_experiment_by_name(experiment_name)    
    from IPython.display import HTML, display
    url = "%s/#mlflow/experiments/%s" % (os.environ["DBJL_HOST"], experiment.experiment_id)
    display(HTML('View the <a href="%s">MLflow experiment</a>' % url))    


experiment_name = <FILL>
home = "/Users/%s" % <FILL>
experiment_name = "%s/experiments/%s" % (home, experiment_name)
remote_mlflow_setup(experiment_name)"""

    print("*** experimental ***")
    name = os.path.splitext(os.path.basename(url))[0]

    resp = requests.get(url)
    if resp.status_code != 200:
        print("error")
    else:
        r = re.compile("<script>(.+?)</script>")
        scripts = r.findall(resp.text)
        script = [s for s in scripts if "__DATABRICKS_NOTEBOOK_MODEL" in s][0]
        r = re.compile("'(.+?)'")
        s = r.findall(script)
        nb = json.loads(unquote(base64.b64decode(s[0]).decode("utf-8")))
        cells = [c["command"] for c in nb["commands"]]
        ipy = {"cells":[wrap("code", cell1), wrap("code", cell2)],  "nbformat": 4, "nbformat_minor": 4, "metadata":{}}
        for c in cells:
            t = "code"            
            if c.startswith("%md"):
                t = "markdown"
                c = c[3:]
            elif c.startswith("%s"):
                # Jupyter uses a cell magic
                c = "%" + c
            ipy["cells"].append(wrap(t, c))
        with open("%s.ipynb" % name, "w") as fd:
            fd.write(json.dumps(ipy))
        print("Downloaded notebook to %s.ipynb" % name)
