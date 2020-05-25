## 5.3 Details

Details to some of the flags of `dj` / `databrickslabs_jupyterlab`

- **-h/--help:** Show help:

    ```bash
    (db-jlab2)$ dj -h

    usage: databrickslabs-jupyterlab [-h] [-b] [-d] [-m] [-D] [-i CLUSTER_ID] [-k]
                                    [-l] [-n NOTEBOOK_URL] [-o ORGANISATION] [-p]
                                    [-r] [-s] [-v] [-V {all,diff,same}] [-w] [-W]
                                    [-B] [-N]
                                    [profile]

    Configure remote Databricks access with JupyterLab

    positional arguments:
    profile               A databricks-cli profile

    optional arguments:
    -h, --help            show this help message and exit
    -b, --bootstrap       Bootstrap the local databrickslabs-jupyterlab
                            environment
    -d, --delete          Delete a jupyter kernelspec
    -m, --mirror          Mirror a a remote Databricks environment
    -D, --debug           Debug calls to REST API
    -i CLUSTER_ID, --id CLUSTER_ID
                            The cluster_id to avoid manual selection
    -k, --kernelspec      Create a kernel specification
    -l, --lab             Safely start JupyterLab
    -n NOTEBOOK_URL, --notebook_url NOTEBOOK_URL
                            Download demo notebook
    -o ORGANISATION, --organisation ORGANISATION
                            The organisation for Azure Databricks
    -p, --profiles        Show all databricks cli profiles and check SSH key
    -r, --reconfigure     Reconfigure cluster with id cluster_id
    -s, --ssh-config      Configure SSH access for a cluster
    -v, --version         Check version of databrickslabs-jupyterlab
    -V {all,diff,same}, --versioncheck {all,diff,same}
                            Check version of local env with remote env
    -w, --whitelist       Use a whitelist (include pkg) of packages to install
                            instead of blacklist (exclude pkg)
    -W, --print-whitelist
                            Print whitelist (include pkg) of packages to install
    -B, --print-blacklist
                            Print blacklist (exclude pkg) of packages to install
    -N, --no-spark        Do not create a Spark Session
    ```

- **-b/--bootstrap:** Bootstrap a local *databrickslabs_jupyterlab* installation

    ```bash
    (db-jlab2)$ dj -b
    ```

    This will load all necessary packaes and labextensions after installaion of *databrickslabs_jupyterlab* via `pip`

- **-d/--delete:** Delete selectively *JupyterLab Integration* kernel specifications

    ```bash
    (db-jlab2)$ dj -d

    ? Which kernel spec to delete (Ctrl-C to finish)?  (Use arrow keys)
    » SSH 0508-164224-fores138 aws-ffm:TEST-6.5.x (db-jlab2/Spark)
      SSH 0508-164224-fores138 aws-ffm:TEST-6.5.x (db-jlab2)
    ```

- **-k/--kernelspec:** Create jupyter kernel for remote cluster

    - Databricks on AWS:

        ```bash
        (db-jlab2)$ dj $PROFILE -k [-i <cluster name>]
        ```

    - Azure:

        ```bash
        (db-jlab2)$ dj $PROFILE -k -o <organisation> [-i <cluster name>]
        ```

    This will execute the following steps:

    - Get host and token from `.databrickscfg` for the given profile
    - In case `-i` is not used, show a list of clusters that have the correct SSH key (id_$PROFILE) configured
    - Installs `databrickslabs_jupyterlab`, `ipykernel` and `ipywidgets` on the remote driver
    - Creates the remote kernel specification

- **-l/--lab:** Safely start JupyterLab

    while you can start JupyterLab via `jupyter lab`, it is recommended to use the wrapper

    ```bash
    (db-jlab2)$ dj $PROFILE -l [-i <cluster name>]
    ```

    It will check whether the remote cluster is up and running, update the ssh info, check the availability of the relevant libs before starting jupyter Lab. 

- **-m/--mirror:** Create a locval mirror of a remote Databricks cluster

    see [Creating a mirror of a remote Databricks cluster](mirrored-environment.md)

- **-n/--notebook_url:** Download a demo notebook from Databricks docs and convert to JupyterLab format

    ```bash
    (db-jlab2)$ dj -n https://docs.databricks.com/_static/notebooks/delta/quickstart-python.html
    
    *** experimental ***
    Downloaded notebook to quickstart-python.ipynb
    ```

    Markdown cells and Databricks notebook magics will be converted to *JupyterLab* magics

- **-o/--organisation**: On Azure provide the organisation id
    see **-k**

- **-p/--profiles: Show currently available profiles:**

    ```bash
    (db-jlab2)$ dj -p

    Valid version of conda detected: 4.7.10

    PROFILE       HOST                                    SSH KEY
    eastus2       https://eastus2.azuredatabricks.net     MISSING
    demo          https://demo.cloud.databricks.com       OK
    ```

    **Note:** If the column *SSH KEY* e.g. for *PROPFILE* "demo" says "MISSING", use

    ```bash
    (db-jlab2)$ ssh-keygen -f ~/.ssh/id_demo -N ""
    ```

    and add `~/.ssh/id_demo.pub` to the SSH config of the respective cluster and restart it.

    Alternatively use `dj $PROFILE -s -i $CLUSTER_ID` (see **-s**)

- **-r/--reconfigure:** Reconfigure cluster with id cluster_id:

    Reconfigure SSH and install driver libraries for a running Databricks cluster

- **-s/--ssh-config:** Configure SSH access

    ```bash
    dj $PROFILE -s -i $CLUSTER_ID
    ```

    For more details see [Configure SSH access](../ssh-configurations.md)

- **-v: Compare local and remote library versions (uses the locally activated canda environment)**

    ```bash
    (db-jlab2)$ dj $PROFILE -v all|same|diff [-i <cluster name>]
    ```

