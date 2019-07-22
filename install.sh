#!/bin/bash
set -e

if [[ "$1" == "" ]]; then
    echo "Usage: $(basename $0) env-name"
    exit 1
fi

envname=$1

conda env create -n $envname -f ./env.yml
source $(conda info | awk '/base env/ {print $4}')/bin/activate $envname

jupyter labextension install @jupyter-widgets/jupyterlab-manager 
# jupyter labextension install @jupyter-widgets/jupyterlab-sidecar
jupyter labextension install jupyterlab_bokeh bqplot@0.4.5
jupyter labextension list

make all


echo -e "\n\n\x1b[32m= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
                              Q U I C K S T A R T
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 

Prerequisites:
--------------

- Install Databricks CLI and configure profile(s) for your cluster(s)

  AWS: https://docs.databricks.com/user-guide/dev-tools/databricks-cli.html)
  Azure: https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html

- Create an ssh key pair called ~/.ssh/id_<profile> for each cluster and 
  add the public key to the cluster SSH configuration


Databricks-jupyterlab:
----------------------

1) Show help

    conda activate $envname
    databricks-jupyterlab -h

2) Create jupyter kernel for remote cluster

    Databricks on AWS:
        databricks-jupyterlab <profile> -k
    
    Azure Databricks:
        databricks-jupyterlab <profile> -k -o <organisation>

3) Copy Personal Access token for databricks cluster to cipboard (same on AWS and Azure)

    databricks-jupyterlab <profile> -c

4) Start jupyter lab to use the kernel(s) created in 2)

    jupyter lab


Currently available profiles (databricks-jupyterlab -p):

$(databricks-jupyterlab -p)


\x1b[0m"