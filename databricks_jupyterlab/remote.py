#   Copyright 2019 Bernhard Walter
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import configparser
import json
import os
import sys
import time
from os.path import expanduser
import socket
import subprocess
import uuid
import glob

from ssh_config import SSHConfig, Host

import inquirer
from inquirer.themes import Default, term

from databricks_cli.configure.provider import get_config, ProfileConfigProvider
from databricks_cli.sdk.api_client import ApiClient
from databricks_cli.clusters.api import ClusterApi

from remote_ikernel.manage import show_kernel, add_kernel
from remote_ikernel.compat import kernelspec as ks

from databricks_jupyterlab.rest import Clusters, Libraries, Command

PIP_INSTALL = "/databricks/python/bin/pip install -q --no-warn-conflicts --disable-pip-version-check"
PIP_LIST = "/databricks/python/bin/pip list --disable-pip-version-check --format=json"


class StatusFile:
    def __init__(self, profile, cluster_id):

        # create status file folder
        status_path = os.path.expanduser("~/.databricks-jupyterlab")
        try:
            if not os.path.exists(status_path):
                os.mkdir(status_path)
            self.ok = True
        except:
            print("Warning: Cannot create %s, no Databricks cluster status in Jupyterlab" % status_path)
            self.ok = False

        # Clean up old startup files
        try:
            self.status_file = os.path.join(status_path, "%s_%s" % (profile, cluster_id))
            os.remove(self.status_file)
            os.remove("%s.starting" % self.status_file)
        except:
            pass

    def log(self, msg):
        if self.ok:
            try:
                with open("%s.starting" % self.status_file, "w") as fd:
                    fd.write(msg)
            except:
                print("Warning: Cannot write to %s, no Databricks cluster status in Jupyterlab" % self.status_file)

    def log_start(self, indicator):
        self.log("Cluster starting" + indicator)

    def log_install_cluster(self, indicator):
        self.log("Installing cluster libs" + indicator)

    def log_ssh(self):
        self.log("Configuring SSH")

    def log_check(self):
        self.log("Checking driver libs")

    def log_install_driver(self):
        self.log("Installing driver libs")

    def log_done(self):
        self.log("Connected")
        self.finish()

    def log_error(self, msg):
        self.log(msg)

    def finish(self):
        if self.ok:
            try:
                os.rename("%s.starting" % self.status_file, self.status_file)
            except:
                print("Warning: Cannot rename %s, no Databricks cluster status in Jupyterlab" % self.status_file)


class Dark(Default):
    def __init__(self):
        super().__init__()
        self.List.selection_color = term.cyan


def bye(msg=None):
    if msg is not None:
        print(msg)
    sys.exit(1)


def ssh(host, cmd):
    try:
        return subprocess.check_output(["ssh", "-o", "StrictHostKeyChecking=no", host, cmd])
    except:
        bye("Error installing package")
        return None


def scp(host, file, target):
    try:
        subprocess.run(["scp", "-q", "-o", "StrictHostKeyChecking=no", "%s" % file, "%s:%s" % (host, target)])
    except:
        bye("Error copying file over ssh")


def run(cmd):
    try:
        subprocess.run(cmd)
    except:
        bye("Error running: %s" % cmd)


def get_db_config(profile, verbose=True):
    config = configparser.ConfigParser()
    config.read(expanduser("~/.databrickscfg"))
    profiles = config.sections()
    if not profile in profiles:
        print(" The profile '%s' is not available in ~/.databrickscfg:" % profile)
        for p in profiles:
            print("- %s" % p)
        bye()
    else:
        host = config[profile]["host"]
        token = config[profile]["token"]
        if verbose:
            print("   => host: %s" % (host))
        return host, token


def connect(profile):
    config = ProfileConfigProvider(profile).get_config()
    verify = config.insecure is None
    if config.is_valid_with_token:
        return ApiClient(host=config.host, token=config.token, verify=verify)
    else:
        bye("Token for profile '%s' is invalid" % profile)


def get_cluster(apiclient, profile, host, token, cluster_id=None):
    with open("%s/.ssh/id_%s.pub" % (expanduser("~"), profile)) as fd:
        try:
            ssh_pub = fd.read().strip()
        except:
            print("ssh key for profile 'id_%s.pub' does not exist in %s/.ssh" % (profile, expanduser("~")))
            bye()
    client = ClusterApi(apiclient)
    clusters = client.list_clusters()
    my_clusters = [
        cluster for cluster in clusters["clusters"]
        if ssh_pub in [c.strip() for c in cluster.get("ssh_public_keys", [])]
    ]

    if cluster_id is None:

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
                          choices=[entry(i, cluster) for i, cluster in enumerate(my_clusters)])
        ]
        answer = inquirer.prompt(choice, theme=Dark())
        cluster = my_clusters[int(answer["cluster_id"].split(":")[0])]
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

    status_file = StatusFile(profile, cluster_id)

    cluster_api = Clusters(url=host, token=token)
    response = cluster_api.status(cluster_id)
    state = response["state"]

    started = False
    if not state in ["RUNNING", "RESIZING"]:
        if state == "TERMINATED":
            print("   => Starting cluster %s" % cluster_id)
            status_file.log_start("")
            started = True
            response = cluster_api.start(cluster_id)

        print("   => Waiting for cluster %s being started (this can take up to 5 min)" % cluster_id)
        print("   ", end="", flush=True)

        indicator = ""
        while not state in ("RUNNING", "RESIZING"):
            print(".", end="", flush=True)
            time.sleep(5)
            indicator += "."
            if len(indicator) == 5:
                indicator = "."
            status_file.log_start(indicator)
            response = cluster_api.status(cluster_id)
            state = response["state"]

        print("\n   => Waiting for libraries on cluster %s being installed (this can take some time)" % cluster_id)
        print("   ", end="", flush=True)

        indicator = ""
        done = False
        while not done:
            status_file.log_install_cluster(indicator)
            states = get_library_state(cluster_id, host=host, token=token)
            installing = any([s in ["PENDING", "RESOLVING", "INSTALLING"] for s in states])
            if installing:
                print(".", end="", flush=True)
                time.sleep(5)
                indicator += "."
                if len(indicator) == 5:
                    indicator = "."
            else:
                done = True
                print("\n   Done\n")

    public_ip = response["driver"]["public_dns"]

    print("   => Selected cluster: %s (%s)" % (cluster_name, public_ip))

    return (cluster_id, public_ip, cluster_name, started, status_file)


def prepare_ssh_config(cluster_id, profile, public_ip):
    config = os.path.join(expanduser("~"), ".ssh/config")
    try:
        sc = SSHConfig.load(config)
    except:
        sc = SSHConfig(config)
    hosts = [h.name for h in sc.hosts()]
    if cluster_id in hosts:
        host = sc.get(cluster_id)
        host.set("HostName", public_ip)
        print("   => Added ssh config entry or modified IP address:")
        print(host)
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
        print("Adding ssh config to ~/.ssh/config")
        print(host)
        sc.append(host)
    sc.write()


def create_kernelspec(profile, organisation, host, cluster_id, cluster_name):
    print("   Creating kernel specification for profile '%s'" % profile)
    env = "DBJL_PROFILE=%s DBJL_HOST=%s DBJL_CLUSTER=%s" % (profile, host, cluster_id)
    if organisation is not None:
        env += " DBJL_ORG=%s" % organisation
    kernel_cmd = "sudo -H %s /databricks/python3/bin/python3 -m ipykernel -f {connection_file}" % env
    add_kernel("ssh",
               name="%s:%s" % (profile, cluster_name),
               kernel_cmd=kernel_cmd,
               language="python",
               workdir="/home/ubuntu",
               host="%s:2200" % cluster_id,
#               ssh_init=json.dumps(["databricks-jupyterlab", profile, "-r", "-i", cluster_id]),
               ssh_timeout="10",
               no_passwords=True,
               verbose=True)

    print("   => Kernel specification 'SSH %s %s' created or updated" % (cluster_id, cluster_name))


def install_libs(host, module_path, ipywidets_version, sidecar_version):

    wheel = glob.glob("%s/lib/*.whl" % module_path)[0]
    target = "/home/ubuntu/%s" % str(uuid.uuid4())

    print("   Installing ipywidgets")
    ssh(host, "sudo -H %s ipywidgets==%s sidecar==%s" % (PIP_INSTALL, ipywidets_version, sidecar_version))

    print("   Installing databricks_jupyterlab")
    ssh(host, "mkdir -p %s" % target)
    scp(host, wheel, target)
    ssh(host, "sudo -H %s --upgrade %s/%s" % (PIP_INSTALL, target, os.path.basename(wheel)))
    ssh(host, "rm -f %s/* && rmdir %s" % (target, target))
    print("   Done")

def mount_sshfs(host):
    ssh(host, "sudo mkdir -p /usr/lib/ssh")
    ssh(host, "sudo ln -s /usr/lib/openssh/sftp-server /usr/lib/ssh/sftp-server")
    run(["mkdir", "-p", "./remotefs/%s" % host])
    try:
        run(["umount", "-f", "./remotefs/%s" % host])
    except:
        pass
    run(["sshfs", "ubuntu@%s:/dbfs" % host, "./remotefs/%s" % host, "-p", "2200"])


def show_profiles():
    template = "%-20s %-60s %s"
    print("")
    print(template % ("PROFILE", "HOST", "SSH KEY"))
    config = configparser.ConfigParser()
    config.read(expanduser("~/.databrickscfg"))
    profiles = config.sections()

    for profile in profiles:
        host, _ = get_db_config(profile, verbose=False)
        ssh_ok = "OK" if os.path.exists(os.path.expanduser("~/.ssh/id_%s") % profile) else "MISSING"
        print(template % (profile, host, ssh_ok))


def get_remote_packages(host):
    return json.loads(ssh(host, PIP_LIST))


def is_reachable(public_dns):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex((public_dns, 2200))
    return result == 0


def get_library_state(clusterId, host, token):
    libraries_api = Libraries(url=host, token=token)
    libraries = libraries_api.status(clusterId)

    if libraries.get("library_statuses", None) is None:
        return []
    else:
        return [lib["status"] for lib in libraries["library_statuses"]]


def check_installed(host):
    packages = get_remote_packages(host)
    found = False
    for p in packages:
        if p["name"] == "databricks-jupyterlab":
            found = True
            break
    return found
