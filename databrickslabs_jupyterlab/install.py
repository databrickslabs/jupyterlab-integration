import os
import subprocess
import sys
import tempfile

import inquirer
from inquirer.themes import Default, term

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.remote import Dark

def print_green(message):
    print("\n\x1b[32m%s\x1b[0m")

def get_env_file(module_path):
    path = os.path.join(module_path, "env_files")
    envs = [e[4:-4] for e in os.listdir(path) if e.startswith("env-")]

    choice = [inquirer.List('env_id', message='Which environment do you want to mirror?', choices=envs)]
    answer = inquirer.prompt(choice, theme=Dark())
    env_file = os.path.join(path, "env-%s.yml" % (answer["env_id"]))
    labext_file = os.path.join(path, "labextensions.txt")

    return labext_file, env_file, answer["env_id"]


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


def install_env(env_file, env_name):
    script = """#!/bin/bash
conda env create -n %s -f %s
source $(conda info | awk '/base env/ {print $4}')/bin/activate "%s" 
pip install --upgrade .
""" % (env_name, env_file, env_name)
    print_green("Installing conda environment")
    execute(script, "install_env.sh", "Error while installing conda environment")


def install_labextensions(labext_file, env_name):
    script = """#!/bin/bash
source $(conda info | awk '/base env/ {print $4}')/bin/activate "%s" 
jupyter labextension install $(cat %s)
jupyter labextension install extensions/databrickslabs_jupyterlab_status
""" % (env_name, labext_file)
    print_green("Installing jupyterlab extensions")
    execute(script, "install_labext.sh", "Error while installing jupyter labextensions")


def install(env_name=None):
    module_path = os.path.dirname(databrickslabs_jupyterlab.__file__)
    labext_file, env_file, proposed_env_name = get_env_file(module_path)
    if env_name is None:
        env_name = proposed_env_name
    install_env(env_file, env_name)
    install_labextensions(labext_file, env_name)
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
