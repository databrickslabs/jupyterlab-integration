# Local JupyterLab connecting to Databricks via SSH

## 1 Prerequisites

- Install Databricks CLI and configure profile(s) for your cluster(s)

  - AWS: https://docs.databricks.com/user-guide/dev-tools/databricks-cli.html)
  - Azure: https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html

- Create an ssh key pair called `~/.ssh/id_<profile>` for each cluster and add the public key to the cluster SSH configuration

## 2 Installation

Clone the repository:

```bash
git clone https://github.com/databrickslabs/Jupyterlab-Integration.git
cd Jupyterlab-Integration
```

Select a conda environment name (e.g. *jlab*) and install databricks-jupyterlab

```bash
./install.sh jlab
```

## 3 Usage

Activate the conda environment for databricks-jupyterlab

```bash
conda activate jlab
```

### 3.1 Quick Start

The quickest way to use databricks-jupyterlab is:

- **Command line**

    Create a kernel, copy token to clipboard and start JupyterLab:

    ```bash
    databricks-jupyterlab <profile> -k -c
    jupyter lab
    ```

- **Notebook**

    Connect to remote Spark context:

    ```python
    [1] from databricks_jupyterlab.connect import dbcontext, is_remote
        dbcontext()
    ```

    This will request you to add the token copied to clipboard above:

    ```
        Sun Jul 14 09:31:16 2019 py4j imported
        Databricks Host: https://demo.cloud.databricks.com
        Cluster Id: xxxx-xxxxxx-xxxxxx
        Enter personal access token |_______________________________|
    ```

    After pressing *Enter*, you will see

    ```
        Gateway created..
        Connected to gateway
        Python interpreter: /databricks/python/bin/python
        Set up Spark progress bar
        The following global variables have been created:
        - spark       Spark session
        - sc          Spark context
        - sqlContext  Hive Context
        - dbutils     Databricks utilities

        ...
    ```

### 3.2 Details

1) **Show help**

    ```bash
    databricks-jupyterlab -h
    ```

2) **Currently available profiles (databricks-jupyterlab -p):**

    ```bash
    databricks-jupyterlab -p
    ```

    **Note:** If the column *SSH KEY* e.g. for *PROPFILE* "demo" says "MISSING", use

    ```bash
    ssh-keygen -f ~/.ssh/id_demo -N ""
    ```

    and add `~/.ssh/id_demo.pub` to the SSH config of the respective cluster and restart it.

3) **Create jupyter kernel for remote cluster**

    - Databricks on AWS:

        ```bash
        databricks-jupyterlab <profile> -k
        ```

    - Azure:

        ```bash
        databricks-jupyterlab <profile> -k -o <organisation>
        ```

    This will execute the following steps:

    - Get host and token from .databrickscfg for the given profile
    - Show a list of clusters that have the correct SSH key (id_<profile>) configured
    - Installs databricks_jupyterlab, ipywidgets on remote driver
    - Creates the remote kernel specification

    **Note:** This needs to be repeated whenever the remote cluster gets restarted (to retrieve the new IP address of the driver)

4) **Copy Personal Access token for databricks cluster to cipboard**

    This is the same command on AWS and Azure

    ```bash
    databricks-jupyterlab <profile> -c
    ```

5) **Start jupyter lab to use the kernel(s) created in 3.**

    ```bash
    jupyter lab
    ```

## 4 Test notebooks

To work with the test notebooks in `./examples` the remote cluster needs to have the following libraries installed:

- bokeh==1.2.0
- bqplot==0.11.5
- mlflow
- spark-sklearn
