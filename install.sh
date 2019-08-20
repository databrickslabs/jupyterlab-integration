#!/bin/bash
set -e

OPTIONS=(
    "No Databricks Runtime (jupyter labs only)"
    "Databricks Runtime 5.5"
    "Databricks Runtime 5.5 ML"
    "Databricks Runtime 5.5 conda (beta)"
)

ENV_FILES=(
    env-jupyter-only.yml
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

ENV_NAME=""
if [[ "$1" != "" ]]; then
    ENV_NAME=$1
fi

ENV_FILE=""
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
    echo "Which remote Databricks Runtime should be mirrored from a Data Science library perspective?"
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
            "${OPTIONS[3]}")
                ENV_FILE=${ENV_FILES[3]}
                break
                ;;
            "quit")
                exit 1
                ;;
        esac
    done
    PS3=$PS3BAK
fi

if [[ "$ENV_NAME" == "" ]]; then
    ENV_NAME=${ENV_FILE%.yml}
    ENV_NAME=${ENV_NAME#env-}
    read -p "Provide cond environment name ($ENV_NAME): " NEW_ENV_NAME
    if [[ "$NEW_ENV_NAME" != "" ]]; then
        ENV_NAME="$NEW_ENV_NAME"
    fi
fi

echo "$ENV_NAME: $ENV_FILE"

echo -e "\n\x1b[32m1 Install conda environment $envname\n\x1b[0m"

conda env create -n $ENV_NAME -f "databrickslabs_jupyterlab/env_files/$ENV_FILE"
source $(conda info | awk '/base env/ {print $4}')/bin/activate "$ENV_NAME"

echo -e "\n\x1b[32m2 Install jupyterlab extensions\n\x1b[0m"

LABEXTS=$(cat databrickslabs_jupyterlab/env_files/labextensions.txt | xargs)
jupyter labextension install --no-build $LABEXTS

cd extensions/databrickslabs_jupyterlab_status
jupyter labextension install
cd ../..
echo

echo -e "\n\x1b[32m3 Install databrickslabs-jupyterlab\n\x1b[0m"

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


databrickslabs-jupyterlab:
--------------------------

1) Show help

    conda activate $ENV_NAME
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


Currently available profiles (databrickslabs-jupyterlab -p):

$(databrickslabs-jupyterlab -p)


\x1b[0m"
