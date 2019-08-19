# Local JupyterLab connecting to Databricks via SSH

This package allows to connect to a remote Databricks cluster from a locally running Jupyter Lab:

![Overview](docs/overview.png)

## 1 Prerequisites

- Install Databricks CLI and configure profile(s) for your cluster(s)

  - AWS: https://docs.databricks.com/user-guide/dev-tools/databricks-cli.html)
  - Azure: https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html

- Create an ssh key pair called `~/.ssh/id_<profile>` for each cluster and add the public key to the cluster SSH configuration

## 2 Installation

Clone the repository:

```bash
(base)$ git clone https://github.com/databrickslabs/Jupyterlab-Integration.git
(base)$ cd Jupyterlab-Integration
```

The local conda environment should resemble the remote Databricks Runtime (DBR) as much as poossible. Therefore Databricks Jupyterlab comes with different environment configuration files for the newest DBRs:

1. `env-dbr-5.5.yml`: Databricks Runtime 5.5
2. `env-dbr-5.5ml.yml`: Databricks Runtime 5.5 ML
3. `env-dbr-5.5conda.yml`: Databricks Runtime 5.5 conda (beta)

Select a conda environment name (e.g. *jlab-5.5-ml*) and install databrickslabs-jupyterlab by calling `install.sh`. The script will show you the available DBR environment options to select from:

```bash
(base)$ ./install.sh jlab-5.5-ml

1) Databricks Runtime 5.5       3) Databricks Runtime 5.5 conda (beta)
2) Databricks Runtime 5.5 ML    4) quit
Select 1-4: 2

jlab-5.5-ml: env-dbr-5.5ml.yml
```

The installation comprises of 3 parts and can take a few minutes:

1. Install conda environment
2. Install jupyterlab extensions
3. Install databrickslabs-jupyterlab

It finishes with an overview of the usage

## 3 Usage

Activate the conda environment for *databrickslabs-jupyterlab*

```bash
(base)$ conda activate jlab-5.5-ml
```

### 3.1 Quick Start

The quickest way to use *databrickslabs-jupyterlab* is:

- **Command line**

    Create a kernel specification and copy token to clipboard (needs to be done once for each new cluster):

    ```bash
    (jlab-5.5-ml)$ databrickslabs-jupyterlab <profile> -k -c
    ```

    Start Jupyter Lab the usual way (a new kernel is available in the kernel change menu)

    ```bash
    (jlab-5.5-ml)$ jupyter lab
    ```

- **Notebook**

    When the cluster is already running the status bar of Jupyter lab should show

    ![kernel ready](docs/connected.png) 

    To connect to the remote Spark context, enter the following two lines into a notebook cell:

    ```python
    [1] from databrickslabs_jupyterlab.connect import dbcontext, is_remote
        dbcontext()
    ```

    This will request you to add the token copied to clipboard above:

    ```
        Fri Aug  9 09:58:04 2019 py4j imported
        Enter personal access token for profile 'demo' |____________________________________|
    ```

    After pressing *Enter*, you will see

    ```
        Gateway created for cluster '0806-143104-skirt84' ... connected
        The following global variables have been created:
        - spark       Spark session
        - sc          Spark context
        - sqlContext  Hive Context
        - dbutils     Databricks utilities
    ```

    Note: `databrickslabs-jupyterlab <profile> -c` let's you quickly copy the token to the clipboard so that you can simply paste the token to the input box.

- **Cluster Auto-Termination**

    Should the cluster auto terminate while the notebook is connected, the status bar will change to

    - ![kernel disconnected](docs/cluster-terminated.png) 

    Clicking on the status bar entry as indicated by the message will open a dialog box to confirm that the remote cluster should be started again. During restart the following status messages will be shown in this order:

    - ![cluster-starting](docs/cluster-starting-2.png)
    - ![installing-cluster-libs](docs/installing-cluster-libs.png)
    - ![checking-driver-libs](docs/checking-driver-libs.png)
    - ![installing-driver-libs](docs/installing-driver-libs.png)

    If the cluster is up and running, however cannot be reached by `ssh` (e.g. VPN not running), then one would see

    - ![cluster unreachable](docs/cluster-unreachable.png)

    In this case check connectivity, e.g. by calling `ssh <cluster_id>` in a terminal window.

    After successful start the status would again show:

    - ![kernel ready](docs/connected.png)

- **Notebook hung after cluster start or kernel change**

    When this happens, usually the local Jupyter lab frontend and the remote kernel are out of sync. Try the following:

    - Save your notebook(s) and refresh the browser page.
    - If it still doesn't work, additinoally restart the kernel

### 3.2 Details

1) **Show help**

    ```bash
    (jlab-5.5-ml)$ databrickslabs-jupyterlab -h
    ```

2) **Show currently available profiles (databrickslabs-jupyterlab -p):**

    ```bash
    (jlab-5.5-ml)$ databrickslabs-jupyterlab -p

    Valid version of conda detected: 4.7.10

    PROFILE              HOST                                                         SSH KEY
    eastus2              https://eastus2.azuredatabricks.net                          MISSING
    demo                 https://demo.cloud.databricks.com                            OK
    ```

    **Note:** If the column *SSH KEY* e.g. for *PROPFILE* "demo" says "MISSING", use

    ```bash
    (jlab-5.5-ml)$ ssh-keygen -f ~/.ssh/id_demo -N ""
    ```

    and add `~/.ssh/id_demo.pub` to the SSH config of the respective cluster and restart it.

3) **Create jupyter kernel for remote cluster**

    - Databricks on AWS:

        ```bash
        (jlab-5.5-ml)$ databrickslabs-jupyterlab <profile> -k [-i <cluster name>]
        ```

    - Azure:

        ```bash
        (jlab-5.5-ml)$ databrickslabs-jupyterlab <profile> -k -o <organisation> [-i <cluster name>]
        ```

    This will execute the following steps:

    - Get host and token from `.databrickscfg` for the given profile
    - In case `-i` is not used, show a list of clusters that have the correct SSH key (id_<profile>) configured
    - Installs `databrickslabs_jupyterlab` and `ipywidgets` on the remote driver
    - Creates the remote kernel specification

4) **Safely start Jupyter Lab**

    while you can start Jupyter Lab via `jupyter lab`, it is recommended to use the wrapper

    ```bash
    (jlab-5.5-ml)$ databrickslabs-jupyterlab <profile> -l [-i <cluster name>]
    ```

    It will check whether the remote cluster is up and running, update the ssh info, check the availability of th relevant libs before starting jupyter Lab.

5) **Copy Personal Access token for databricks workspace to the clipboard**

    This is the same command on AWS and Azure

    ```bash
    (jlab-5.5-ml)$ databrickslabs-jupyterlab <profile> -c
    ```

6) **Compare local and remote library versions (uses the locally activated canda environment)**

    ```bash
    (jlab-5.5-ml)$ databrickslabs-jupyterlab <profile> -v all|same|diff [-i <cluster name>]
    ```

## 4 Test notebooks

To work with the test notebooks in `./examples` the remote cluster needs to have the following libraries installed:

- bokeh==1.2.0
- bqplot==0.11.5
- mlflow==1.0.0
- spark-sklearn
