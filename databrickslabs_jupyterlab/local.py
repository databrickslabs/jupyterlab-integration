import configparser
import os
import subprocess
import sys
import textwrap
from os.path import expanduser
from ssh_config import SSHConfig, Host

class Colors:
    ERROR = '\033[91m'
    OK = '\033[92m'
    WARNING = '\033[93m'
    RESET = '\033[0m'

def _print(color, *args):
    print(color, end="")
    print(*args, end="")
    print(Colors.RESET)

def print_ok(*args):
    _print(Colors.OK, *args)

def print_error(*args):
    _print(Colors.ERROR, *args)

def print_warning(*args):
    _print(Colors.WARNING, *args)

def bye(status=0):
    """Standard exit function
    
    Args:
        msg (str, optional): Exit message to be printed. Defaults to None.
    """
    if status != 0:
        print_error("\n=> Exiting")
    sys.exit(status)


def conda_version():
    """Check conda version"""
    try:
        result = subprocess.check_output(["conda", "--version"])
    except Exception as ex:
        print(ex)
        print("conda cannot be called. Is it properly installed?")
        sys.exit(1)

    result = result.strip().decode()
    return tuple([int(v) for v in result.split(" ")[1].split(".")])


def write_config():
    """Store jupyter lab configuration necessary for databrickslabs_jupyterlab
    Set values:
    - c.KernelManager.autorestart: False
    - c.MappingKernelManager.kernel_info_timeout: 600
    """
    config = {"c.KernelManager.autorestart": False, "c.MappingKernelManager.kernel_info_timeout": 600}

    config_file = os.path.expanduser("~/.jupyter/jupyter_notebook_config.py")
    if os.path.exists(config_file):
        with open(config_file, "r") as fd:
            lines = fd.read().split("\n")

        with open(config_file, "w") as fd:
            for line in lines:
                kv = line.strip().split("=")
                if len(kv) == 2:
                    k, v = kv
                    if config.get(k, None) is not None:
                        fd.write("%s=%s\n" % (k, config[k]))
                        del config[k]
                    else:
                        fd.write("%s\n" % line)
            for k, v in config.items():
                fd.write("%s=%s\n" % (k, v))
    else:
        with open(config_file, "w") as fd:
            fd.write("\n".join(["%s=%s" % (k, v) for k, v in config.items()]))


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
        bye()
    else:
        host = config[profile]["host"]
        token = config[profile]["token"]
        return host, token


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

