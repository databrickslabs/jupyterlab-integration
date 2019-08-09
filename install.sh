#!/bin/bash
set -e

OPTIONS=(
    "Databricks Runtime 5.5"
    "Databricks Runtime 5.5 ML"
    "Databricks Runtime 5.5 conda (beta)"
)

ENV_FILES=(
    env-dbr-5.5.yml
    env-dbr-5.5ml.yml
    env-dbr-5.5conda.yml
)
function usage {
    echo -e "\nUsage: $(basename $0) env-name [env-file-id]"
    echo -e "\nValid env-file-id's are:"
    for i in "${!OPTIONS[@]}"; do 
        printf " %s = %s\n" "$[$i+1]" "${OPTIONS[$i]}"
    done
    echo
    exit 1
}

if [[ "$1" == "" ]]; then
    echo -e "\nMissing name of new environment (env-name)"
    usage
fi

ENV_NAME=$1

if [[ "$2" != "" ]]; then
    if [[ $2 < 1 || $2 > ${#OPTIONS[@]} ]]; then
        echo -e "\nWrong DBR runtime id (env-file-id)"
        usage
    else
        ENV_FILE=${ENV_FILES[$[$2-1]]}
    fi
else
    PS3BAK=$PS3
    PS3="Select 1-$[${#OPTIONS[@]}+1]: "

    select opt in "${OPTIONS[@]}" "quit"; do
        case $opt in
            "${OPTIONS[0]}")
                ENV_FILE=${ENV_FILES[0]}
                break
                ;;
            "${OPTIONS[1]}")
                ENV_FILE=${ENV_FILES[1]}
                break
                ;;
            "${OPTIONS[2]}")
                ENV_FILE=${ENV_FILES[2]}
                break
                ;;
            "quit")
                exit 1
                ;;
        esac
    done
    PS3=$PS3BAK
fi

echo "$ENV_NAME: $ENV_FILE"

echo -e "\n\x1b[32m1 Install conda environment $envname\n\x1b[0m"

conda env create -n $ENV_NAME -f "$ENV_FILE"
source $(conda info | awk '/base env/ {print $4}')/bin/activate "$ENV_NAME"

echo -e "\n\x1b[32m2 Install jupyterlab extensions\n\x1b[0m"

jupyter labextension install --no-build $(cat labextensions.txt)
cd extensions/databricks_jupyterlab_status
jupyter labextension install
cd ../..
echo

echo -e "\n\x1b[32m3 Install databricks-jupyterlab\n\x1b[0m"

pip install --upgrade .


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

    conda activate $ENV_NAME
    databricks-jupyterlab -h

2) Create jupyter kernel for remote cluster

    Databricks on AWS:
        databricks-jupyterlab <profile> -k
    
    Azure Databricks:
        databricks-jupyterlab <profile> -k -o <organisation>

3) Compare local and remote python package versions
    
    databricks-jupyterlab <profile> -v all|same|diff

4) Copy Personal Access token for databricks cluster to cipboard (same on AWS and Azure)

    databricks-jupyterlab <profile> -c

5) Start jupyter lab to use the kernel(s) created in 2)

    jupyter lab


Currently available profiles (databricks-jupyterlab -p):

$(databricks-jupyterlab -p)


\x1b[0m"
