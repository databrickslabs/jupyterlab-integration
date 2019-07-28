import argparse
import json
import os
from subprocess import check_output

from remote_ikernel.kernel import RemoteIKernel 

import databricks_jupyterlab
from databricks_jupyterlab.remote import (get_db_config, get_cluster, connect, prepare_ssh_config,
                                          get_remote_packages, is_reachable, create_kernelspec,
                                          install_libs, mount_sshfs, show_profiles, bye)

def start_remote_kernel():
    """
    Read command line arguments and initialise a kernel.
    """
    # These will not face a user since they are interpreting the command from
    # kernel the kernel.json
    description = "Prepare ssh config"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--profile')
    parser.add_argument('--host')
    args = parser.parse_args()

    print("\n* Getting host and token from .databrickscfg")
    host, token = get_db_config(args.profile)

    print("\n* Select remote cluster")
    apiclient = connect(args.profile)
    cluster_id = args.host.split(":")[0]
    cluster_id, public_ip, cluster_name, started = get_cluster(apiclient, args.profile, host, token, cluster_id)
    if cluster_name is None:
        raise Exception("Error: cluster_id '%s' not found" % cluster_id)
        

    print("\n* Configuring ssh config for remote cluster")
    prepare_ssh_config(cluster_id, args.profile, public_ip)
    if not is_reachable(public_ip):
        error = "Cannot connect to remote cluster. Please check:"
        error += "\n- whether port 2200 is open in cloud security group"
        error += "\n- whether VPN is enabled if you need one to connect to the cluster"
        raise Exception(error)
    
    if started:
        print("\n* Installing databricks_jupyterlab, ipywidgets on remote driver")
        module_path = os.path.dirname(databricks_jupyterlab.__file__)
        packages = json.loads(check_output(["conda", "list", "--json"]))
        deps = {p["name"]:p["version"]  for p in packages if p["name"] in ["ipywidgets", "sidecar"]}    
        install_libs(cluster_id, module_path, ipywidets_version=deps["ipywidgets"], sidecar_version=deps["sidecar"])



start_remote_kernel()
