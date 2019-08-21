import json
import os
import re
import subprocess
import sys
import tempfile

import inquirer
from inquirer.themes import Default, term

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.remote import ssh, Dark, get_remote_packages

# os.environ.get("DATABRICKS_RUNTIME_VERSION", None) == "5.5"
# os.environ.get("CONDA_EXE", None) == "/databricks/conda/bin/conda"
# os.environ.get("DATABRICKS_ROOT_CONDA_ENV", None) == "databricks-standard"

WHITELIST = [
    "hyperopt", "keras-applications", "keras-preprocessing", "keras", "matplotlib", "mleap", "mlflow", "numba", "numpy",
    "pandas", "patsy", "pillow", "pyarrow", "python-dateutil", "pyparsing", "scikit-learn", "scipy", "seaborn",
    "simplejson", "statsmodels", "tabulate", "tensorboard", "tensorboardx", "tensorflow-estimator", "tensorflow",
    "torch", "torchvision"
]


def print_green(message):
    print("\n\x1b[32m%s\x1b[0m" % message)


def execute(script, script_name, message):
    with tempfile.TemporaryDirectory() as tmpdir:
        script_file = os.path.join(tmpdir, script_name)
        with open(script_file, "w") as fd:
            fd.write(script)

        try:
            result = subprocess.call(["bash", script_file])
            if result != 0:
                sys.exit(1)
        except Exception as ex:
            print(message, ex)
            sys.exit(1)


def update_env(env_file):
    script = """#!/bin/bash
conda env update --file %s
""" % (env_file)
    print_green("Updating current conda environment")
    execute(script, "update_env.sh", "Error while updating conda environment")


def install_env(env_file, env_name=None):
    script = """#!/bin/bash
conda env create -n %s -f %s
source $(conda info | awk '/base env/ {print $4}')/bin/activate "%s" 
""" % (env_name, env_file, env_name)

    print_green("Installing conda environment %s" % env_name)
    execute(script, "install_env.sh", "Error while installing conda environment")


def install_labextensions(labext_file, env_name=None):
    if env_name is None:
        script = """#!/bin/bash
jupyter labextension install $(cat %s)
""" % labext_file
    else:
        script = """#!/bin/bash
source $(conda info | awk '/base env/ {print $4}')/bin/activate "%s" 
jupyter labextension install $(cat %s)
""" % (env_name, labext_file)

    print_green("Installing jupyterlab extensions")
    execute(script, "install_labext.sh", "Error while installing jupyter labextensions")


def update_local():
    module_path = os.path.dirname(databrickslabs_jupyterlab.__file__)

    env_file = os.path.join(module_path, "lib/env.yml")
    update_env(env_file)

    labext_file = os.path.join(module_path, "lib/labextensions.txt")
    install_labextensions(labext_file)
    usage(os.environ.get("CONDA_DEFAULT_ENV", "unknown"))


def install(profile, cluster_id, cluster_name):
    print("\n* Installation of local environment to mirror a remote Databricks cluster")

    libs = get_remote_packages(cluster_id)
    ds_libs = [lib for lib in libs if lib["name"].lower() in WHITELIST]

    ds_yml = ""
    for lib in ds_libs:
        if lib["name"] == "hyperopt":
            r = re.compile(r"(\d+\.\d+.\d+)(.*)")
            version = r.match(lib["version"]).groups()[0]
        else:
            version = lib["version"]
        ds_yml += ("    - %s==%s\n" % (lib["name"], version))
    print("\n    Library versions being installed:")
    print(ds_yml + "\n")

    module_path = os.path.dirname(databrickslabs_jupyterlab.__file__)
    env_file = os.path.join(module_path, "lib/env.yml")
    with open(env_file, "r") as fd:
        master_yml = fd.read()
        
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = os.path.join(tmpdir, "env.yml")
        with open(env_file, "w") as fd:
            fd.write(master_yml)
            fd.write("\n    # Data Science Libs\n")
            fd.write(ds_yml)
            fd.write("\n")

        env_name = cluster_name.replace(" ", "_")
        answer = input("    => Provide a conda environment name (default = %s): " % env_name)
        if answer != "":
            env_name = answer.replace(" ", "_")

        install_env(env_file, env_name)

        labext_file = os.path.join(module_path, "lib/labextensions.txt")
        install_labextensions(labext_file, env_name)

    usage(env_name)


def usage(env_name):
    print_green("""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
                              Q U I C K S T A R T
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 

Prerequisites:
--------------

- Install Databricks CLI and configure profile(s) for your cluster(s)

  AWS: https://docs.databricks.com/user-guide/dev-tools/databricks-cli.html)
  Azure: https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html

- Create an ssh key pair called ~/.ssh/id_<profile> for each cluster and 
  add the public key to the cluster SSH configuration


databrickslabs-jupyterlab:
--------------------------

1) Show help

    conda activate %s
    databrickslabs-jupyterlab -h

2) Create jupyter kernel for remote cluster

    Databricks on AWS:
        databrickslabs-jupyterlab <profile> -k [-i cluster-id]
    
    Azure Databricks:
        databrickslabs-jupyterlab <profile> -k -o <organisation>

3) Compare local and remote python package versions
    
    databrickslabs-jupyterlab <profile> -v all|same|diff

4) Copy Personal Access token for databricks cluster to cipboard (same on AWS and Azure)

    databrickslabs-jupyterlab <profile> -c

5) Start jupyter lab to use the kernel(s) created in 2)

    databrickslabs-jupyterlab <profile> -l [-i cluster-id]


6) Check currently available profiles 

    databrickslabs-jupyterlab -p

""" % env_name)
