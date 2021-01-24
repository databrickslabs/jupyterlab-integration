import base64
import json
import os
import re
import time
from os.path import expanduser
import socket
from urllib.parse import unquote

import requests

from databricks_cli.configure.provider import ProfileConfigProvider
from databricks_cli.sdk.api_client import ApiClient
from databricks_cli.clusters.api import ClusterApi
from databricks_cli.libraries.api import LibrariesApi

# import databrickslabs_jupyterlab
from databrickslabs_jupyterlab._version import __version__
from databrickslabs_jupyterlab.rest import Command, DatabricksApiException
from databrickslabs_jupyterlab.utils import (
    bye,
    print_ok,
    print_error,
    print_warning,
    question,
    utf8_decode,
    execute,
)
from databrickslabs_jupyterlab.local import execute, get_local_libs


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
        api_client = ApiClient(host=config.host, token=config.token, verify=verify)
        api_client.default_headers["user-agent"] = "databrickslabs-jupyterlab-%s" % __version__
        return api_client
    else:
        print_error(
            "No token found for profile '%s'.\nUsername/password in .databrickscfg is not supported by databrickslabs-jupyterlab"
            % profile
        )
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
            return "%s: '%s' (id: %s, state: %s, workers: %d)" % (
                i,
                cluster["cluster_name"],
                cluster["cluster_id"],
                cluster["state"],
                cluster["num_workers"],
            )
        else:
            return "%s: '%s' (id: %s, state: %s, scale: %d-%d)" % (
                i,
                cluster["cluster_name"],
                cluster["cluster_id"],
                cluster["state"],
                cluster["autoscale"]["min_workers"],
                cluster["autoscale"]["max_workers"],
            )

    answer = question(
        "cluster_id",
        "Which cluster to connect to?",
        [entry(i, cluster) for i, cluster in enumerate(clusters)],
    )
    if answer["cluster_id"] is None:
        return None
    else:
        return clusters[int(answer["cluster_id"].split(":")[0])]


def get_cluster(profile, cluster_id=None, status=None):
    """Get the cluster configuration from remote

    Args:
        profile (str): Databricks CLI profile string
        cluster_id (str, optional): If cluster_id is given, users will not be asked to select one.
                                    Defaults to None.
        status (Status, optional): A Status class providing set_status. Defaults to None.
        tunnel (str, optional): An ssh tunne geiven as "address:port"

    Returns:
        tuple: Cluster configs: cluster_id, public_ip, cluster_name and a flag
                                whether it was started

    Returns:
        tuple: (cluster_id, public_ip, cluster_name, started)
    """

    if os.environ.get("SSH_TUNNEL") is None:
        tunnel = None
    else:
        tunnel = os.environ.get("SSH_TUNNEL")
        print_warning("\n  ==> Using tunnel: " + tunnel + "\n")

    failure = (None, None, None, None)

    with open("%s/.ssh/id_%s.pub" % (expanduser("~"), profile)) as fd:
        try:
            ssh_pub = fd.read().strip()
        except:  # pylint: disable=bare-except
            print_error(
                "   Error: ssh key for profile 'id_%s.pub' does not exist in %s/.ssh"
                % (profile, expanduser("~"))
            )
            bye()

    try:
        apiclient = connect(profile)
        client = ClusterApi(apiclient)
        clusters = client.list_clusters()
    except Exception as ex:  # pylint: disable=broad-except
        print_error(ex)
        return failure

    clusters = clusters["clusters"]

    if cluster_id is not None:
        cluster = None
        for c in clusters:
            if c["cluster_id"] == cluster_id:
                cluster = c
                break

        if cluster is None:
            print_error(
                "   Error: A cluster with id '%s' does not exist in the workspace of profile '%s'"
                % (cluster_id, profile)
            )
            return failure

        if ssh_pub not in [c.strip() for c in cluster.get("ssh_public_keys", [])]:
            print_error(
                "   Error: Cluster with id '%s' does not have ssh key '~/.ssh/id_%s' configured"
                % (cluster_id, profile)
            )
            return failure
    else:
        my_clusters = [
            cluster
            for cluster in clusters
            if ssh_pub in [c.strip() for c in cluster.get("ssh_public_keys", [])]
        ]

        if not my_clusters:
            print_error(
                (
                    "    Error: There is no cluster in the workspace for profile '%s' "
                    + "configured with ssh key '~/.ssh/id_%s':"
                )
                % (profile, profile)
            )
            print(
                (
                    "    Use 'databrickslabs_jupyterlab %s -s' to configure ssh for clusters "
                    + "in this workspace\n"
                )
                % profile
            )
            return failure

        current_conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
        found = None
        ind = -1
        for i, c in enumerate(my_clusters):
            if c["cluster_name"].replace(" ", "_") == current_conda_env:
                found = c["cluster_name"]
                ind = i
                break

        if found is not None:
            print_warning(
                ("\n   => The current conda environment is '%s'. " + current_conda_env)
                + (
                    "\n      You might want to select cluster %d with the name '%s'?\n"
                    % (ind, found)
                )
            )

        cluster = select_cluster(my_clusters)
        if cluster is None:
            return failure

    cluster_id = cluster["cluster_id"]
    cluster_name = cluster["cluster_name"]

    try:
        response = client.get_cluster(cluster_id)
    except Exception as ex:  # pylint: disable=broad-except
        print_error(ex)
        return failure

    state = response["state"]
    if not state in ["RUNNING", "RESIZING"]:
        if state == "TERMINATED":
            print("   => Starting cluster %s" % cluster_id)
            if status is not None:
                status.set_status(profile, cluster_id, "Cluster Starting")
            try:
                response = client.start_cluster(cluster_id)
            except Exception as ex:  # pylint: disable=broad-except
                print_error(ex)
                return failure

        print("   => Waiting for cluster %s being started (this can take up to 5 min)" % cluster_id)
        print("   ", end="", flush=True)

        while not state in ("RUNNING", "RESIZING"):
            if status is not None:
                status.set_status(profile, cluster_id, "Cluster Starting", False)
            print(".", end="", flush=True)
            time.sleep(5)
            try:
                response = client.get_cluster(cluster_id)
            except Exception as ex:  # pylint: disable=broad-except
                print_error(ex)
                return failure

            if response.get("error", None) is not None:
                print_error(response["error"])
                return failure
            else:
                state = response["state"]
        print_ok("\n   => OK")

        if status is not None:
            status.set_status(profile, cluster_id, "Cluster started")

        print(
            "\n   => Waiting for libraries on cluster %s being installed (this can take some time)"
            % cluster_id
        )
        print("   ", end="", flush=True)

        done = False
        while not done:
            try:
                states = get_library_state(profile, cluster_id)
            except DatabricksApiException as ex:
                print_error(ex)
                return failure

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

    if tunnel is not None:
        address = tunnel
    else:
        public_dns = response["driver"].get("public_dns")
        if public_dns is None:
            print_error("   Error: Cluster does not have public DNS name")
            return failure
        address = "%s:%s" % (public_dns, 2200)

    print_ok("   => Selected cluster: %s (%s)" % (cluster_name, address))

    return (cluster_id, address, cluster_name, None)


def get_python_path(host, conda_env=None):  # pylint: disable=unused-argument
    python_path = "/databricks/python/bin"
    return python_path


def install_libs(cluster_id, host, token):
    """Install ipywidgets, databrickslabs_jupyterlab libraries on the driver

    Args:
        host (str): host from databricks cli config for given profile string
        python_path (str): Remote python path to be used for kernel
    """
    python_path = get_python_path(cluster_id)

    packages = get_local_libs()
    deps = {p["name"]: p["version"] for p in packages if p["name"] in ["ipywidgets", "ipykernel"]}
    libs = [
        "ipywidgets==%s" % deps["ipywidgets"],
        "ipykernel==%s" % deps["ipykernel"],
        "databrickslabs-jupyterlab==%s" % __version__,
        "pygments>=2.4.1",
    ]

    print("   => Installing ", " ".join(libs))

    ssh = os.environ.get("SSH") or "ssh"
    cmd = [ssh, cluster_id, "sudo", python_path + "/pip", "install", "--upgrade"] + libs
    result = execute(cmd)

    if result["returncode"] == 0:
        if result["stdout"].startswith("Requirement already satisfied"):
            return (0, "Requirement already satisfied")
        else:
            return (0, "Installed")

    return (result["returncode"], result["stdout"] + "\n" + result["stderr"])


def get_remote_packages(cluster_id, host, token):
    cmd = (
        "import sys, pkg_resources, json; "
        + 'print(json.dumps([{"name": "python", "version": "%d.%d" % (sys.version_info.major, sys.version_info.minor)}] + '
        + '[{"name":p.key, "version":p.version} for p in pkg_resources.working_set]))'
    )
    try:
        command = Command(url=host, cluster_id=cluster_id, token=token)
        result = command.execute(cmd)
        command.close()
    except DatabricksApiException as ex:
        print(ex)
        return None
    return result


def is_reachable(endpoint):
    """Check whether a remote cluster is reachable

    Args:
        endpoint (str): Public IP address or DNS name and port as "address:port"

    Returns:
        bool: True if reachable else False
    """
    # return subprocess.call(["nc", "-z", address, str(port)]) == 0
    address, port = endpoint.split(":")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex((address, int(port)))
        result = result == 0
    except:  # pylint: disable=bare-except
        result = False

    sock.close()
    return result


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
    except Exception as ex:  # pylint: disable=broad-except
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
            key
            for key in joint_keys
            if deps.get(key, None) != remote_deps.get(key, None)
            # and deps.get(key, None) is not None and remote_deps.get(key, None) is not None
        ]
    for key in scope:
        result = "%-30s %-10s  %-10s" % (key, deps.get(key, "--"), remote_deps.get(key, "--"))
        if deps.get(key) == remote_deps.get(key):
            print_ok(result)
        else:
            print_error(result)


def configure_ssh(profile, cluster_id):
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
            result = execute(["ssh-keygen", "-b", "2048", "-N", "", "-f", sshkey_file])
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
    except Exception as ex:  # pylint: disable=broad-except
        print_error(ex)
        return None

    try:
        response = client.get_cluster(cluster_id)
    except Exception as ex:  # pylint: disable=broad-except
        print_error(ex)
        return None

    ssh_public_keys = response.get("ssh_public_keys", [])
    if sshkey in [key.strip() for key in ssh_public_keys]:
        print_ok("   => public ssh key already configured for cluster %s" % cluster_id)
        bye()

    request = {}

    for key, val in response.items():
        if key not in [
            "driver",
            "executors",
            "spark_context_id",
            "state",
            "state_message",
            "start_time",
            "terminated_time",
            "last_state_loss_time",
            "last_activity_time",
            "disk_spec",
        ]:  # omit runtime attributes
            request[key] = val

    request["ssh_public_keys"] = ssh_public_keys + [sshkey]

    print_warning(
        "   => The ssh key will be added to the cluster."
        + "\n   Note: The cluster will be restarted immediately!"
    )
    answer = input(
        "   => Shall the ssh key be added and the cluster be restarted (y/n)? (default = n): "
    )
    if answer.lower() == "y":
        try:
            response = client.edit_cluster(request)
        except DatabricksApiException as ex:
            print_error(str(ex))
            return None
        print_ok("   => OK")
    else:
        print_error("   => Cancelled")


def download_notebook(url, prefix="."):
    """Download Databricks demo notebooks from docs.databricks.com.
    It adds two cells on the top to initialize the Databricks context and MLflow

    Args:
        url (str): The HTML url copied from the "Get notebook link"
    """

    def wrap(typ, cell):
        return {
            "cell_type": typ,
            "source": cell,
            "outputs": [],
            "metadata": {},
            "execution_count": 0,
        }

    #     cell1 = """# Retrieve Spark Context
    # from databrickslabs_jupyterlab.connect import dbcontext
    # from databrickslabs_jupyterlab.remote import is_remote
    # dbcontext()"""

    #     cell2 = """# Setup MLflow (optional)
    # import os
    # from mlflow
    # from mlflow.tracking import MlflowClient

    # def remote_mlflow_setup(experiment_name):
    #     mlflow.set_experiment(experiment_name)
    #     experiment = MlflowClient().get_experiment_by_name(experiment_name)
    #     from IPython.display import HTML, display
    #     url = "%s/#mlflow/experiments/%s" % (os.environ["DBJL_HOST"], experiment.experiment_id)
    #     display(HTML('View the <a href="%s">MLflow experiment</a>' % url))

    # experiment_name = <FILL>
    # home = "/Users/%s" % <FILL>
    # experiment_name = "%s/experiments/%s" % (home, experiment_name)
    # remote_mlflow_setup(experiment_name)"""

    cell = "**Downloaded by Databrickslabs Jupyterlab**"

    print("*** experimental ***")
    name = os.path.splitext(os.path.basename(url))[0]

    if url.startswith("http"):
        resp = requests.get(url)
        if resp.status_code != 200:
            print("error")
            return
        code = resp.text
    else:
        with open(url, "r") as fd:
            code = fd.read()

    r = re.compile("<script>(.+?)</script>")
    scripts = r.findall(code)
    script = [s for s in scripts if "__DATABRICKS_NOTEBOOK_MODEL" in s][0]
    r = re.compile("'(.+?)'")
    s = r.findall(script)
    nb = json.loads(unquote(base64.b64decode(s[0]).decode("utf-8")))
    language = nb["language"]
    cells = [c["command"] for c in nb["commands"]]
    ipy = {
        # "cells": [wrap("code", cell1), wrap("code", cell2)],
        "cells": [wrap("markdown", cell)],
        "nbformat": 4,
        "nbformat_minor": 4,
        "metadata": {},
    }

    for c in cells:
        t = "code"
        if c.startswith("%md"):
            t = "markdown"
            c = c[3:]
            r = re.compile(r"(#+)([^#\s])")
            c = r.sub(r"\1 \2", c)
        elif c.startswith("%python"):
            c = c[8:]
        elif c.startswith("%sql"):
            c = c.replace("%sql", "%%sql\n")
        elif c.startswith("%sh"):
            c = c.replace("%sh", "%%sh\n")
        elif c.startswith("%scala"):
            c = c.replace("%scala", "%%scala\n")
        else:
            if language != "python":
                c = "%%" + language + "\n" + c

        # SQL cells can have multiple statements separated by ";" in Databricks.
        # So split them in sigle cells for Jupyterlab Integration
        if c.startswith("%%sql"):
            # remove potential trailing ";" and then split at ";" to get all SQL statements
            lines = c[5:].strip(";").split(";")
            for line in lines:
                ipy["cells"].append(wrap(t, "%%sql\n" + line))
        else:
            ipy["cells"].append(wrap(t, c))

    with open(os.path.join(prefix, "%s.ipynb" % name), "w") as fd:
        fd.write(json.dumps(ipy))

    print("Downloaded notebook to %s.ipynb" % name)
