import json
import os
import sys
import time
from os.path import expanduser
import socket
import subprocess
import uuid
import glob

import inquirer
from inquirer.themes import Default, term

from databricks_cli.configure.provider import get_config, ProfileConfigProvider
from databricks_cli.sdk.api_client import ApiClient
from databricks_cli.clusters.api import ClusterApi

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.rest import Clusters, Libraries, DatabricksApiException
from databrickslabs_jupyterlab.local import (bye, print_ok, print_error, print_warning)


class Dark(Default):
    """Dark Theme for inquirer"""
    def __init__(self):
        super().__init__()
        self.List.selection_color = term.cyan


def ssh(host, cmd):
    """Execute an ssh command
    
    Args:
        host (str): Hostname or ssh host alias
        cmd (str): Command to execute
    
    Returns:
        str: Commend result or in error case None
    """
    try:
        return subprocess.check_output(["ssh", "-o", "StrictHostKeyChecking=no", host, cmd])
    except:
        print_error("Error installing package")
        bye(1)
        return None


def scp(host, file, target):
    """Copy a file to the remote host via scp
    
    Args:
        host (str): Hostname or ssh host alias
        file (str): file name of the file to be copied
        target (str): target folder or path
    """
    try:
        subprocess.run(["scp", "-q", "-o", "StrictHostKeyChecking=no", "%s" % file, "%s:%s" % (host, target)])
    except:
        print_error("Error copying file over ssh")
        bye()


def run(cmd):
    """Run a shell command
    
    Args:
        cmd (str): shell command
    """
    try:
        subprocess.run(cmd)
    except:
        print_error("Error running: %s" % cmd)
        bye(1)


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
            return "%s: %s (id: %s, state: %s, workers: %d)" % (i, cluster["cluster_name"], cluster["cluster_id"],
                                                                cluster["state"], cluster["num_workers"])
        else:
            return "%s: %s (id: %s, state: %s, scale: %d-%d)" % (i, cluster["cluster_name"], cluster["cluster_id"],
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

    apiclient = connect(profile)
    client = ClusterApi(apiclient)
    clusters = client.list_clusters()
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

        cluster = select_cluster(my_clusters)

    cluster_id = cluster["cluster_id"]
    cluster_name = cluster["cluster_name"]

    cluster_api = Clusters(url=host, token=token)
    try:
        response = cluster_api.status(cluster_id)
    except DatabricksApiException as ex:
        print_error(ex)
        return (None, None, None, None)

    state = response["state"]

    started = False
    if not state in ["RUNNING", "RESIZING"]:
        if state == "TERMINATED":
            print("   => Starting cluster %s" % cluster_id)
            if status is not None:
                status.set_status(profile, cluster_id, "Cluster Starting")
            started = True
            try:
                response = cluster_api.start(cluster_id)
            except DatabricksApiException as ex:
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
                response = cluster_api.status(cluster_id)
            except DatabricksApiException as ex:
                print_error(ex)
                return (None, None, None, None)

            if response.get("error", None) is not None:
                print("ERROR", response)
                state = "UNKNOWN"
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
                states = get_library_state(cluster_id, host=host, token=token)
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

    public_ip = response["driver"]["public_dns"]

    print_ok("   => Selected cluster: %s (%s)" % (cluster_name, public_ip))

    return (cluster_id, public_ip, cluster_name, started)


def get_pip(host, flags):
    conda_env = ssh(host, "echo $DEFAULT_DATABRICKS_ROOT_CONDA_ENV").strip().decode("utf-8")
    if len(conda_env) == 0: 
        # no conda DBR
        python_path = "/databricks/python3/bin/python"
    else:
        python_path = "/databricks/conda/envs/%s/bin/python" % conda_env

    return "%s %s" % (python_path, flags)
    
    
def install_libs(host):
    """Install ipywidgets, sidecar and databrickslabs_jupyterlab libraries on the driver
    
    Args:
        host (str): host from databricks cli config for given profile string
        module_path (str): The local module path where databrickslabs_jupyterlab is installed
        ipywidets_version (str): The version of ipywidgets used locally
        sidecar_version (str): The version of ipywidgets used locally
    """
    pip_flags = "-m pip install -q --no-warn-conflicts --disable-pip-version-check"
    pip = get_pip(host, pip_flags)

    module_path = os.path.dirname(databrickslabs_jupyterlab.__file__)

    wheel = glob.glob("%s/lib/*.whl" % module_path)[0]
    target = "/home/ubuntu/%s" % str(uuid.uuid4())

    print("   => Installing ipywidgets")
    packages = json.loads(subprocess.check_output(["conda", "list", "--json"]))
    deps = {p["name"]: p["version"] for p in packages if p["name"] in ["ipywidgets", "sidecar"]}
    ssh(host, "sudo -H %s ipywidgets==%s sidecar==%s" % (pip, deps["ipywidgets"], deps["sidecar"]))

    print("   => Installing databrickslabs_jupyterlab")
    ssh(host, "mkdir -p %s" % target)
    scp(host, wheel, target)
    ssh(host, "sudo -H %s --upgrade %s/%s" % (pip, target, os.path.basename(wheel)))
    ssh(host, "rm -f %s/* && rmdir %s" % (target, target))


def mount_sshfs(host):
    """Mount remote driver filesystem via sshfs
    Needs Fuse running on local machine
    
    Args:
        host (str): host from databricks cli config for given profile string
    """
    ssh(host, "sudo mkdir -p /usr/lib/ssh")
    ssh(host, "sudo ln -s /usr/lib/openssh/sftp-server /usr/lib/ssh/sftp-server")
    run(["mkdir", "-p", "./remotefs/%s" % host])
    try:
        run(["umount", "-f", "./remotefs/%s" % host])
    except:
        pass
    run(["sshfs", "ubuntu@%s:/dbfs" % host, "./remotefs/%s" % host, "-p", "2200"])


def get_remote_packages(host):
    """List all packages installed on remote cluster
    
    Args:
        host (str): host from databricks cli config for given profile string
    
    Returns:
        list(dict): List of pip list --format=json
    """
    pip_flags = "-m pip list --disable-pip-version-check --format=json"
    pip = get_pip(host, pip_flags)
    return json.loads(ssh(host, pip))


def is_reachable(public_dns):
    """Check whether a remote cluster is reachable
    
    Args:
        public_dns (str): Public IP address or DNS name
    
    Returns:
        bool: True if reachable else False
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex((public_dns, 2200))
    return result == 0


def get_library_state(cluster_id, host, token):
    """Get the state of the library installation on the remote cluster
    
    Args:
        cluster_id (str): Cluster ID
        host (str): host from databricks cli config for given profile string
        token (str): token from databricks cli config for given profile stringf
    
    Returns:
        list: list of installation status for each custom library
    """
    libraries_api = Libraries(url=host, token=token)
    libraries = libraries_api.status(cluster_id)

    if libraries.get("library_statuses", None) is None:
        return []
    else:
        return [lib["status"] for lib in libraries["library_statuses"]]


def check_installed(host):
    """Check whether databrickslabs_jupyterlab is installed on the remote host
    
    Args:
    host (str): host from databricks cli config for given profile string
    
    Returns:
        bool: True if installed else False
    """
    packages = get_remote_packages(host)
    found = False
    for p in packages:
        if p["name"] == "databrickslabs-jupyterlab":
            found = True
            break
    return found


def version_check(cluster_id, flag):
    """Compare local and remote library versions
    
    Args:
        cluster_id (str): Cluster ID
    """
    def normalize(key):
        return key.lower().replace("-", "_")

    packages = json.loads(subprocess.check_output(["conda", "list", "--json"]))
    deps = {normalize(p["name"]): p["version"] for p in packages}

    remote_packages = get_remote_packages(cluster_id)
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
            subprocess.call(["ssh-keygen", "-b", "2048",  "-N", "", "-f",  sshkey_file])
            print_ok("   => OK")
        else:
            bye()
    else:
        print_ok("\n   => ssh key '%s' already exists" % sshkey_file)

    with open(sshkey_file + ".pub", "r") as fd:
        sshkey = fd.read().strip()

    cluster_api = Clusters(url=host, token=token)
    try:
        response = cluster_api.status(cluster_id)
    except DatabricksApiException as ex:
        print_error(ex)
        return None

    ssh_public_keys = response.get("ssh_public_keys", [])
    if sshkey in [key.strip() for key in ssh_public_keys]:
        print_ok("   => public ssh key already configured for cluster %s" % cluster_id)
        bye()

    request = {}
    for key in ["cluster_id", "cluster_name", "spark_version", "node_type_id"]:
        request[key] = response[key]
    
    if response.get("num_workers", None) is not None:
        request["num_workers"] = response["num_workers"]

    if response.get("autoscale", None) is not None:
        request["autoscale"] = response["autoscale"]

    request["ssh_public_keys"] = ssh_public_keys + [sshkey]

    print_warning("   => The ssh key will be added to the cluster. \n   Note: The cluster will be restarted immediately!")
    answer = input("   => Shall the ssh key be added and the cluster be restarted (y/n)? (default = n): ")
    if answer.lower() == "y":
        try:
            response = cluster_api.edit(request)
        except DatabricksApiException as ex:
            print_error(str(ex))
            return None
        print_ok("   => OK")
    else:
        print_error("   => Cancelled")
