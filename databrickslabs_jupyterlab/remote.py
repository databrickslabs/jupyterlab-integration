import configparser
import json
import os
import sys
import time
from os.path import expanduser
import socket
import subprocess
import textwrap
import uuid
import glob

from ssh_config import SSHConfig, Host

import inquirer
from inquirer.themes import Default, term

from databricks_cli.configure.provider import get_config, ProfileConfigProvider
from databricks_cli.sdk.api_client import ApiClient
from databricks_cli.clusters.api import ClusterApi

from databrickslabs_jupyterlab.rest import Clusters, Libraries, DatabricksApiException

PIP_INSTALL = "/databricks/python/bin/pip install -q --no-warn-conflicts --disable-pip-version-check"
PIP_LIST = "/databricks/python/bin/pip list --disable-pip-version-check --format=json"


class Dark(Default):
    """Dark Theme for inquirer"""
    def __init__(self):
        super().__init__()
        self.List.selection_color = term.cyan


def bye(msg=None):
    """Standard exit function
    
    Args:
        msg (str, optional): Exit message to be printed. Defaults to None.
    """
    if msg is not None:
        print(msg)
    sys.exit(1)


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
        bye("Error installing package")
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
        bye("Error copying file over ssh")


def run(cmd):
    """Run a shell command
    
    Args:
        cmd (str): shell command
    """
    try:
        subprocess.run(cmd)
    except:
        bye("Error running: %s" % cmd)


def get_db_config(profile):
    """Get Databricks configuration from ~/.databricks.cfg for given profile
    
    Args:
        profile (str): Databricks CLI profile string
    
    Returns:
        tuple: The tuple of host and personal access token from ~/.databrickscfg
    """
    config = configparser.ConfigParser()
    configs = config.read(expanduser("~/.databrickscfg"))
    if not configs:
        bye("Cannot read ~/.databrickscfg")
    
    profiles = config.sections()
    if not profile in profiles:
        print(" The profile '%s' is not available in ~/.databrickscfg:" % profile)
        for p in profiles:
            print("- %s" % p)
        bye()
    else:
        host = config[profile]["host"]
        token = config[profile]["token"]
        return host, token


def connect(profile):
    """Initialize Databricks API client
    
    Args:
        profile (str): Databricks CLI profile string
    
    Returns:
        ApiClient: Databricks ApiClient object
    """
    config = ProfileConfigProvider(profile).get_config()
    if config is None:
        bye("Cannot initialize ApiClient")
    verify = config.insecure is None
    if config.is_valid_with_token:
        return ApiClient(host=config.host, token=config.token, verify=verify)
    else:
        bye("Token for profile '%s' is invalid" % profile)

def _select_cluster(clusters):
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
            return "%s: %s (id: %s, state: %s, scale: %d-%d)" % (
                i, cluster["cluster_name"], cluster["cluster_id"], cluster["state"],
                cluster["autoscale"]["min_workers"], cluster["autoscale"]["max_workers"])

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
    """
    with open("%s/.ssh/id_%s.pub" % (expanduser("~"), profile)) as fd:
        try:
            ssh_pub = fd.read().strip()
        except:
            print("ssh key for profile 'id_%s.pub' does not exist in %s/.ssh" % (profile, expanduser("~")))
            bye()

    apiclient = connect(profile)
    client = ClusterApi(apiclient)
    clusters = client.list_clusters()
    my_clusters = [
        cluster for cluster in clusters["clusters"]
        if ssh_pub in [c.strip() for c in cluster.get("ssh_public_keys", [])]
    ]

    if cluster_id is None:
        cluster = _select_cluster(my_clusters)
    else:
        cluster = None
        for c in my_clusters:
            if c["cluster_id"] == cluster_id:
                cluster = c
                break
        if cluster is None:
            return cluster_id, None, None, None, None

    cluster_id = cluster["cluster_id"]
    cluster_name = cluster["cluster_name"]

    cluster_api = Clusters(url=host, token=token)
    try:
        response = cluster_api.status(cluster_id)
    except DatabricksApiException as ex:
        print(ex)
        return None

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
                print(ex)
                return None

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
                print(ex)
                return None

            if response.get("error", None) is not None:
                print("ERROR", response)
                state = "UNKNOWN"
            else: 
                state = response["state"]
        
        if status is not None:
            status.set_status(profile, cluster_id, "Cluster started")
        
        print("\n   => Waiting for libraries on cluster %s being installed (this can take some time)" % cluster_id)
        print("   ", end="", flush=True)

        done = False
        while not done:
            try:
                states = get_library_state(cluster_id, host=host, token=token)
            except DatabricksApiException as ex:
                print(ex)
                return None
            installing = any([s in ["PENDING", "RESOLVING", "INSTALLING"] for s in states])
            if installing:
                if status is not None:
                    status.set_status(profile, cluster_id, "Installing cluster libraries", False)
                print(".", end="", flush=True)
                time.sleep(5)
            else:
                done = True
                print("\n   => Done\n")

    public_ip = response["driver"]["public_dns"]

    print("   => Selected cluster: %s (%s)" % (cluster_name, public_ip))

    return (cluster_id, public_ip, cluster_name, started)


def prepare_ssh_config(cluster_id, profile, public_ip):
    """Add/edit the ssh configuration belonging to the given cluster in ~/.ssh/config
    
    Args:
        cluster_id (str): Cluster ID
        profile (str): Databricks CLI profile string
        public_ip (str): Public IP address
    """
    config = os.path.join(expanduser("~"), ".ssh/config")
    try:
        sc = SSHConfig.load(config)
    except:
        sc = SSHConfig(config)
    hosts = [h.name for h in sc.hosts()]
    if cluster_id in hosts:
        host = sc.get(cluster_id)
        host.set("HostName", public_ip)
        print("   => Added ssh config entry or modified IP address:\n")
        print(textwrap.indent(str(host), "      "))
    else:
        attrs = {
            'HostName': public_ip,
            'IdentityFile': '~/.ssh/id_%s' % profile,
            'Port': 2200,
            'User': 'ubuntu',
            'ServerAliveInterval': 300,
            'ServerAliveCountMax': 2
        }
        host = Host(name=cluster_id, attrs=attrs)
        print("Adding ssh config to ~/.ssh/config:\n")
        print(textwrap.indent(str(host), "      "))
        sc.append(host)
    sc.write()


def create_kernelspec(profile, organisation, host, cluster_id, cluster_name):
    """Create or edit the remote_ikernel specification for jupyter lab
    
    Args:
        profile (str): Databricks CLI profile string    
        organisation (str): In case of Azure, the organization ID, else None
        host (str): host from databricks cli config for given profile string
        cluster_id (str): Cluster ID
        cluster_name (str): Cluster name
    """
    from remote_ikernel.manage import show_kernel, add_kernel
    from remote_ikernel.compat import kernelspec as ks

    print("   => Creating kernel specification for profile '%s'" % profile)
    env = "DBJL_PROFILE=%s DBJL_HOST=%s DBJL_CLUSTER=%s" % (profile, host, cluster_id)
    if organisation is not None:
        env += " DBJL_ORG=%s" % organisation
    kernel_cmd = "sudo -H %s /databricks/python/bin/python -m ipykernel -f {connection_file}" % env
    add_kernel(
        "ssh",
        name="%s:%s" % (profile, cluster_name),
        kernel_cmd=kernel_cmd,
        language="python",
        workdir="/home/ubuntu",
        host="%s:2200" % cluster_id,
        #               ssh_init=json.dumps(["databrickslabs-jupyterlab", profile, "-r", "-i", cluster_id]),
        ssh_timeout="10",
        no_passwords=True,
        verbose=True)

    print("   => Kernel specification 'SSH %s %s' created or updated" % (cluster_id, cluster_name))


def install_libs(host, module_path, ipywidets_version, sidecar_version):
    """Install ipywidgets, sidecar and databrickslabs_jupyterlab libraries on the driver
    
    Args:
        host (str): host from databricks cli config for given profile string
        module_path (str): The local module path where databrickslabs_jupyterlab is installed
        ipywidets_version (str): The version of ipywidgets used locally
        sidecar_version (str): The version of ipywidgets used locally
    """
    wheel = glob.glob("%s/lib/*.whl" % module_path)[0]
    target = "/home/ubuntu/%s" % str(uuid.uuid4())

    print("   => Installing ipywidgets")
    ssh(host, "sudo -H %s ipywidgets==%s sidecar==%s" % (PIP_INSTALL, ipywidets_version, sidecar_version))

    print("   => Installing databrickslabs_jupyterlab")
    ssh(host, "mkdir -p %s" % target)
    scp(host, wheel, target)
    ssh(host, "sudo -H %s --upgrade %s/%s" % (PIP_INSTALL, target, os.path.basename(wheel)))
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


def show_profiles():
    """Show locally configured Databricks CLI profile"""
    template = "%-20s %-60s %s"
    print("")
    print(template % ("PROFILE", "HOST", "SSH KEY"))
    config = configparser.ConfigParser()
    config.read(expanduser("~/.databrickscfg"))
    profiles = config.sections()

    for profile in profiles:
        host, _ = get_db_config(profile)
        ssh_ok = "OK" if os.path.exists(os.path.expanduser("~/.ssh/id_%s") % profile) else "MISSING"
        print(template % (profile, host, ssh_ok))


def get_remote_packages(host):
    """List all packages installed on remote cluster
    
    Args:
        host (str): host from databricks cli config for given profile string
    
    Returns:
        list(dict): List of pip list --format=json
    """
    return json.loads(ssh(host, PIP_LIST))


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
