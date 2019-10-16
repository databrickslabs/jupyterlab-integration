import configparser
import json
from jupyter_client import kernelspec
import os
import shutil
import subprocess
import sys
import textwrap
import time
from os.path import expanduser
from ssh_config import SSHConfig, Host
import inquirer

from databrickslabs_jupyterlab.utils import (bye, Dark, print_ok, print_error, print_warning)

# add all missing keys to ssh_config
Host.attrs += [
    ("Host", str),
    ("CanonicalizeFallbackLocal", str),
    ("CanonicalizeHostname", str),
    ("CanonicalizeMaxDots", str),
    ("CanonicalizePermittedCNAMEs", str),
    ("CASignatureAlgorithms", str),
    ("CertificateFile", str),
    ("ChallengeResponseAuthentication", str),
    ("CheckHostIP", str),
    ("Ciphers", str),
    ("ClearAllForwardings", str),
    ("Compression", str),
    ("ConnectionAttempts", str),
    ("ConnectTimeout", str),
    ("ControlMaster", str),
    ("ControlPath", str),
    ("ControlPersist", str),
    ("DynamicForward", str),
    ("EnableSSHKeysign", str),
    ("EscapeChar", str),
    ("ExitOnForwardFailure", str),
    ("FingerprintHash", str),
    ("ForwardX11", str),
    ("ForwardX11Timeout", str),
    ("ForwardX11Trusted", str),
    ("GatewayPorts", str),
    ("GlobalKnownHostsFile", str),
    ("GSSAPIAuthentication", str),
    ("GSSAPIDelegateCredentials", str),
    ("HashKnownHosts", str),
    ("HostbasedAuthentication", str),
    ("HostbasedKeyTypes", str),
    ("HostKeyAlgorithms", str),
    ("HostKeyAlias", str),
    ("IdentitiesOnly", str),
    ("IgnoreUnknown", str),
    ("Include", str),
    ("IPQoS", str),
    ("KbdInteractiveAuthentication", str),
    ("KbdInteractiveDevices", str),
    ("KexAlgorithms", str),
    ("MACs", str),
    ("NoHostAuthenticationForLocalhost", str),
    ("NumberOfPasswordPrompts", str),
    ("PasswordAuthentication", str),
    ("PermitLocalCommand", str),
    ("PKCS11Provider", str),
    ("ProxyJump", str),
    ("ProxyUseFdpass", str),
    ("PubkeyAcceptedKeyTypes", str),
    ("PubkeyAuthentication", str),
    ("RekeyLimit", str),
    ("RemoteCommand", str),
    ("RemoteForward", str),
    ("RequestTTY", str),
    ("RevokedHostKeys", str),
    ("SendEnv", str),
    ("ServerAliveCountMax", str),
    ("SetEnv", str),
    ("StreamLocalBindMask", str),
    ("StreamLocalBindUnlink", str),
    ("StrictHostKeyChecking", str),
    ("SyslogFacility", str),
    ("TCPKeepAlive", str),
    ("Tunnel", str),
    ("TunnelDevice", str),
    ("UpdateHostKeys", str),
    ("UseKeychain", str),
    ("UserKnownHostsFile", str),
    ("VerifyHostKeyDNS", str),
    ("VisualHostKey", str),
    ("XAuthLocation", str)
]

def utf8_decode(text):
    if isinstance(text, str):
        return text
        
    try:
        return text.decode("utf-8")
    except:
        # ok, let's replace the "bad" characters
        return text.decode("utf-8", "replace")

def execute(cmd):
    """Execute suprpcess
    
    Args:
        cmd (list(str)): Command as list of cmd parts (e.g. ["ls", "-l"])
    """
    try:
        # Cannot use encoding arg at the moment, since need to support python 3.5
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE).__dict__
        result["stderr"] = utf8_decode(result["stderr"])
        result["stdout"] = utf8_decode(result["stdout"])
        return result
    except Exception as ex:
        return {'args': cmd, 'returncode': -1, 'stdout': '', 'stderr': str(ex)}


def conda_version():
    """Check conda version"""
    result = execute(["conda", "--version"])
    if result["returncode"] != 0:
        print_error(result["stderr"])
        sys.exit(1)

    result = result["stdout"].strip()
    return tuple([int(v) for v in result.split(" ")[1].split(".")])


def write_config():
    """Store jupyter lab configuration necessary for databrickslabs_jupyterlab
    Set values:
    - c.KernelManager.autorestart: False
    - c.MappingKernelManager.kernel_info_timeout: 600
    """
    config = {"c.KernelManager.autorestart": False, "c.MappingKernelManager.kernel_info_timeout": 600}

    full_path = os.path.expanduser("~/.jupyter")
    if not os.path.exists(full_path):
        os.mkdir(full_path)

    config_file = os.path.join(full_path, "jupyter_notebook_config.py")
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


def get_local_libs():
    """Get installed libraries of the currtent conda environment
    """
    result = execute(["conda", "list", "--json"])
    if result["returncode"] != 0:
        print_error(result["stderr"])
        return False

    try:
        return json.loads(result["stdout"])
    except Exception as ex:
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
        bye()
    else:
        host = config[profile]["host"]
        token = config[profile]["token"]
        return host, token

def add_known_host(public_dns, known_hosts="~/.ssh/known_hosts"):
    result = execute(["ssh-keygen", "-R", "[%s]:2200" % public_dns])
    result = execute(["ssh-keyscan", "-p", "2200", public_dns])
    if result["returncode"] == 0:
        fingerprint = result["stdout"]
        known_hosts_file = os.path.expanduser(known_hosts)
        with open(known_hosts_file, "a") as fd:
            fd.write("\n%s" % fingerprint)
        print("   => Known hosts fingerprint added for %s\n" % public_dns)
    else:
        print_warning("   => Could not add know_hosts fingerprint for %s\n" % public_dns)

def prepare_ssh_config(cluster_id, profile, public_dns):
    """Add/edit the ssh configuration belonging to the given cluster in ~/.ssh/config
    
    Args:
        cluster_id (str): Cluster ID
        profile (str): Databricks CLI profile string
        public_dns (str): Public DNS/IP address
    """
    backup_path = "~/.databrickslabs_jupyterlab/ssh_config_backup"

    config = os.path.expanduser("~/.ssh/config")
    if not os.path.exists(os.path.expanduser(backup_path)):
        os.makedirs(os.path.expanduser(backup_path))

    print_warning("   => ~/.ssh/config will be changed")
    backup = "%s/config.%s" % (backup_path, time.strftime("%Y-%m-%d_%H-%M-%S"))
    print_warning("   => A backup of the current ~/.ssh/config has been created")
    print_warning("   => at %s" % backup)

    shutil.copy(config, os.path.expanduser(backup))
    try:
        sc = SSHConfig.load(config)
    except:
        sc = SSHConfig(config)
    hosts = [h.name for h in sc.hosts()]
    if cluster_id in hosts:
        host = sc.get(cluster_id)
        host.set("HostName", public_dns)
        host.set("ServerAliveInterval", 5)
        host.set("ServerAliveCountMax", 2)
        host.set("ConnectTimeout", 5)
        print("   => Added ssh config entry or modified IP address:\n")
        print(textwrap.indent(str(host), "      "))
    else:
        # ServerAliveInterval * ServerAliveCountMax = 48h
        attrs = {
            "HostName": public_dns,
            "IdentityFile": "~/.ssh/id_%s" % profile,
            "Port": 2200,
            "User": "ubuntu",
            "ServerAliveInterval": 30,
            "ServerAliveCountMax": 5760,
            "ConnectTimeout": 5
        }
        host = Host(name=cluster_id, attrs=attrs)
        print("   => Adding ssh config to ~/.ssh/config:\n")
        print(textwrap.indent(str(host), "      "))
        sc.append(host)
    sc.write()

    add_known_host(public_dns)

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


def create_kernelspec(profile, organisation, host, cluster_id, cluster_name, local_env, python_path):
    """Create or edit the ssh_ipykernel specification for jupyter lab
    
    Args:
        profile (str): Databricks CLI profile string    
        organisation (str): In case of Azure, the organization ID, else None
        host (str): host from databricks cli config for given profile string
        cluster_id (str): Cluster ID
        cluster_name (str): Cluster name
        local_env (str): Name of the local conda environment
        python_path (str): Remote python path to be used for kernel
    """
    from ssh_ipykernel.manage import add_kernel

    print("   => Creating kernel specification for profile '%s'" % profile)
    env = "DBJL_PROFILE=%s DBJL_HOST=%s DBJL_CLUSTER=%s" % (profile, host, cluster_id)
    if organisation is not None:
        env += " DBJL_ORG=%s" % organisation
    
    if cluster_name.replace(" ", "_") == local_env:
        display_name = "SSH %s %s:%s" % (cluster_id, profile, cluster_name)
    else:
        display_name = "SSH %s %s:%s (%s)" % (cluster_id, profile, cluster_name, local_env)

    add_kernel(
        host=cluster_id,
        display_name=display_name,
        local_python_path=sys.executable,
        remote_python_path=os.path.dirname(python_path),
        sudo=True,
        env=env,
        timeout=5
    )   
    print("   => Kernel specification 'SSH %s %s' created or updated" % (cluster_id, display_name))

def remove_kernelspecs():
    km = kernelspec.KernelSpecManager()

    kernel_id = None
    while kernel_id != "done":

        remote_kernels = {
            kernelspec.get_kernel_spec(k).display_name : k
            for k, v in kernelspec.find_kernel_specs().items() if k.startswith("ssh_")
        }
        if remote_kernels == {}:
            print_ok("   => No databricklabs_jupyterlab kernel spec left")
            break

        choice = [
            inquirer.List("kernel_name",
                        message="Which kernel spec to delete (Ctrl-C to finish)?",
                        choices=list(remote_kernels.keys()))
        ]
        answer = inquirer.prompt(choice, theme=Dark())

        if answer is None:
            break

        kernel_name = answer["kernel_name"]
        if kernel_id != "done":
            answer = input("Really delete kernels spec '%s' (y/n) " % kernel_name)
            if answer.lower() == "y":
                km.remove_kernel_spec(remote_kernels[kernel_name])
