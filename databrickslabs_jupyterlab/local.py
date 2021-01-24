import configparser
import json
import os
import shutil
import sys
import time
from os.path import expanduser

from jupyter_client import kernelspec
from .ssh_config import SshConfig

from databrickslabs_jupyterlab.utils import (
    bye,
    print_ok,
    print_error,
    print_warning,
    question,
    execute,
)

PREFIX = "ssh_"


def conda_version():
    """Check conda version"""
    result = execute(["conda", "--version"])
    if result["returncode"] != 0:
        print_error(result["stderr"])
        sys.exit(1)

    if result["stdout"].startswith("conda"):
        return result["stdout"].strip().split(" ")[1]
    elif result["stderr"].startswith("conda"):
        return result["stderr"].strip().split(" ")[1]
    else:
        return None


def write_config():
    """Store jupyter lab configuration necessary for databrickslabs_jupyterlab
    Set values:
    - c.KernelManager.autorestart: False
    - c.MappingKernelManager.kernel_info_timeout: 600
    """
    config = {
        "c.KernelManager.autorestart": False,
        "c.MappingKernelManager.kernel_info_timeout": 20,
    }
    c1, c2 = list(config.keys())
    full_path = os.path.expanduser("~/.jupyter")
    if not os.path.exists(full_path):
        os.mkdir(full_path)
    config_file = os.path.join(full_path, "jupyter_notebook_config.py")
    lines = []
    if os.path.exists(config_file):
        with open(config_file, "r") as fd:
            lines = fd.read().split("\n")
        # avoid growing by one empty line for each run
        if lines[-1] == "":
            lines = lines[:-1]
    with open(config_file, "w") as fd:
        for line in lines:
            if line.startswith(c1) or line.startswith(c2):
                kv = line.split("=")
                k = kv[0].strip()
                if config.get(k) is not None:  #  if None it's a duplicate, so ignore
                    fd.write("%s = %s\n" % (k, config[k]))
                    del config[k]
            else:
                # else just copy line
                fd.write("%s\n" % line)
        # write all missing configs
        fd.write("\n".join(["%s = %s" % (k, v) for k, v in config.items()]))


def get_local_libs():
    """Get installed libraries of the currtent conda environment"""
    result = execute(["conda", "list", "--json"])
    if result["returncode"] != 0:
        print_error(result["stderr"])
        return False

    try:
        return json.loads(result["stdout"])
    except Exception as ex:  # pylint: disable=broad-except
        print_error(ex)
        return False


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
        print_error("Cannot read ~/.databrickscfg")
        bye(1)

    profiles = config.sections()
    if not profile in profiles:
        print(" The profile '%s' is not available in ~/.databrickscfg:" % profile)
        for p in profiles:
            print("- %s" % p)
        bye(1)
    else:
        host = config[profile]["host"]
        token = config[profile]["token"]
        return host, token


def add_known_host(address, port, known_hosts="~/.ssh/known_hosts"):
    result = execute(["ssh-keygen", "-R", "[%s]:%s" % (address, port)])
    result = execute(["ssh-keyscan", "-p", str(port), address])
    if result["returncode"] == 0:
        fingerprint = result["stdout"]
        known_hosts_file = os.path.expanduser(known_hosts)
        with open(known_hosts_file, "a") as fd:
            fd.write("\n%s" % fingerprint)
        print("   => Known hosts fingerprint added for %s:%s\n" % (address, port))
    else:
        print_warning("   => Could not add know_hosts fingerprint for %s:%s\n" % (address, port))


def prepare_ssh_config(cluster_id, profile, endpoint):
    """Add/edit the ssh configuration belonging to the given cluster in ~/.ssh/config

    Args:
        cluster_id (str): Cluster ID
        profile (str): Databricks CLI profile string
        endpoint (str): Public DNS/IP address and Port as "address:port"
    """
    backup_path = "~/.databrickslabs_jupyterlab/ssh_config_backup"

    config = os.path.expanduser("~/.ssh/config")
    if not os.path.exists(os.path.expanduser(backup_path)):
        os.makedirs(os.path.expanduser(backup_path))

    data = ""
    if os.path.exists(config):
        print_warning("   => ~/.ssh/config will be changed")
        backup = "%s/config.%s" % (backup_path, time.strftime("%Y-%m-%d_%H-%M-%S"))
        print_warning("   => A backup of the current ~/.ssh/config has been created")
        print_warning("   => at %s" % backup)

        shutil.copy(config, os.path.expanduser(backup))
        with open(config, "r") as fd:
            data = fd.read()

    ssh_config = SshConfig(data)

    host = ssh_config.get_host(cluster_id)
    if host is None:
        host = ssh_config.add_host(cluster_id)

    address, port = endpoint.split(":")
    host.set_param("HostName", address)
    host.set_param("IdentityFile", "~/.ssh/id_%s" % profile)
    host.set_param("Port", port)
    host.set_param("User", "ubuntu")
    host.set_param("ServerAliveInterval", 30)
    host.set_param("ServerAliveCountMax", 5760)
    host.set_param("ConnectTimeout", 5)

    print(f"   => Jupyterlab Integration made the following changes to {config}:")
    ssh_config.dump()
    with open(config, "w") as fd:
        fd.write(ssh_config.to_string())

    add_known_host(address, port)


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


def create_kernelspec(
    profile,
    organisation,
    host,
    cluster_id,
    cluster_name,
    local_env,
    python_path,
    no_spark,
    extra_env="",
):
    """Create or edit the ssh_ipykernel specification for jupyter lab

    Args:
        profile (str): Databricks CLI profile string
        organisation (str): In case of Azure, the organization ID, else None
        host (str): host from databricks cli config for given profile string
        cluster_id (str): Cluster ID
        cluster_name (str): Cluster name
        local_env (str): Name of the local conda environment
        python_path (str): Remote python path to be used for kernel
        extra_env (str): Env vars to add to the remote notebook like "V1=ABC V2=DEF"
    """
    from ssh_ipykernel.manage import add_kernel  # pylint: disable=import-outside-toplevel

    print("   => Creating kernel specification for profile '%s'" % profile)
    env = "DBJL_PROFILE=%s DBJL_HOST=%s DBJL_CLUSTER=%s" % (profile, host, cluster_id)
    if organisation is not None:
        env += " DBJL_ORG=%s" % organisation
    if extra_env != "":
        env = env + " " + extra_env

    if cluster_name.replace(" ", "_") == local_env:
        display_name = "SSH %s %s:%s" % (cluster_id, profile, cluster_name)
        if not no_spark:
            display_name += "(Spark)"
    else:
        display_name = "SSH %s %s:%s (%s%s)" % (
            cluster_id,
            profile,
            cluster_name,
            local_env,
            ("" if no_spark else "/Spark"),
        )

    add_kernel(
        host=cluster_id,
        display_name=display_name,
        local_python_path=sys.executable,
        remote_python_path=os.path.dirname(python_path),
        sudo=True,
        env=env,
        timeout=5,
        module="databrickslabs_jupyterlab",
        opt_args=["--no-spark"] if no_spark else [],
    )
    print("   => Kernel specification '%s' created or updated" % (display_name))


def remove_kernelspecs():
    km = kernelspec.KernelSpecManager()

    while True:

        remote_kernels = {
            kernelspec.get_kernel_spec(k).display_name: k
            for k, v in kernelspec.find_kernel_specs().items()
            if k.startswith("ssh_")
        }
        if remote_kernels == {}:
            print_ok("   => No databricklabs_jupyterlab kernel spec left")
            break

        answer = question(
            "kernel_name",
            "Which kernel spec to delete (Ctrl-C to finish)?",
            list(remote_kernels.keys()),
        )
        kernel_name = answer["kernel_name"]

        if kernel_name is None:
            break

        answer = input("Really delete kernels spec '%s' (y/n) " % kernel_name)
        if answer.lower() == "y":
            km.remove_kernel_spec(remote_kernels[kernel_name])
