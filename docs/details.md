[< back](../README.md)

## 5 Details

- **Show help**

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab -h

    usage: databrickslabs-jupyterlab [-h] [-b] [-d] [-m] [-c] [-i CLUSTER_ID] [-k]
                                    [-l] [-o ORGANISATION] [-p] [-r] [-s] [-v]
                                    [-V {all,diff,same}] [-w] [-W] [-B]
                                    [profile]

    Configure remote Databricks access with Jupyter Lab

    positional arguments:
    profile               A databricks-cli profile

    optional arguments:
    -h, --help            show this help message and exit
    -b, --bootstrap       Bootstrap the local databrickslabs-jupyterlab
                            environment
    -d, --delete          Delete a jupyter kernelspec
    -m, --mirror          Mirror a a remote Databricks environment
    -c, --clipboard       Copy the personal access token to the clipboard
    -i CLUSTER_ID, --id CLUSTER_ID
                            The cluster_id to avoid manual selection
    -k, --kernelspec      Create a kernel specification
    -l, --lab             Safely start Jupyter Lab
    -o ORGANISATION, --organisation ORGANISATION
                            The organisation for Azure Databricks
    -p, --profiles        Show all databricks cli profiles and check SSH key
    -r, --reconfigure     Reconfigure cluster with id cluster_id
    -s, --ssh-config      Configure SSH acces for a cluster
    -v, --version         Check version of databrickslabs-jupyterlab
    -V {all,diff,same}, --versioncheck {all,diff,same}
                            Check version of local env with remote env
    -w, --whitelist       Use a whitelist (include pkg) of packages to install
                            instead of blacklist (exclude pkg)
    -W, --print-whitelist
                            Print whitelist (include pkg) of packages to install
    -B, --print-blacklist
                            Print blacklist (exclude pkg) of packages to install
    ```

- **Show currently available profiles (databrickslabs-jupyterlab -p):**

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab -p

    Valid version of conda detected: 4.7.10

    PROFILE       HOST                                    SSH KEY
    eastus2       https://eastus2.azuredatabricks.net     MISSING
    demo          https://demo.cloud.databricks.com       OK
    ```

    **Note:** If the column *SSH KEY* e.g. for *PROPFILE* "demo" says "MISSING", use

    ```bash
    (db-jlab)$ ssh-keygen -f ~/.ssh/id_demo -N ""
    ```

    and add `~/.ssh/id_demo.pub` to the SSH config of the respective cluster and restart it.

    Alternatively use `databrickslabs-jupyterlab $PROFILE -s -i $CLUSTER_ID` (see below)

- **Create jupyter kernel for remote cluster**

    - Databricks on AWS:

        ```bash
        (db-jlab)$ databrickslabs-jupyterlab $PROFILE -k [-c] [-i <cluster name>]
        ```

    - Azure:

        ```bash
        (db-jlab)$ databrickslabs-jupyterlab $PROFILE -k -o <organisation> [-c] [-i <cluster name>]
        ```

    This will execute the following steps:

    - Get host and token from `.databrickscfg` for the given profile
    - In case `-i` is not used, show a list of clusters that have the correct SSH key (id_$PROFILE) configured
    - In case `-c`is used the Personal access token of the $PROFILE will be copied to the clipboard
    - Installs `databrickslabs_jupyterlab` and `ipywidgets` on the remote driver
    - Creates the remote kernel specification

- **Safely start Jupyter Lab**

    while you can start Jupyter Lab via `jupyter lab`, it is recommended to use the wrapper

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -l [-c] [-i <cluster name>]
    ```

    It will check whether the remote cluster is up and running, update the ssh info, check the availability of th relevant libs before starting jupyter Lab. In case `-c`is used the Personal access token of the $PROFILE will be copied to the clipboard

- **Copy Personal Access token for databricks workspace to the clipboard**

    This is the same command on AWS and Azure

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -c
    ```

- **Compare local and remote library versions (uses the locally activated canda environment)**

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -v all|same|diff [-i <cluster name>]
    ```

- **Configure SSH access**

    ```bash
    databrickslabs-jupyterlab $PROFILE -s -i $CLUSTER_ID
    ```

    For more details see [Configure SSH access](ssh-configurations.md)
