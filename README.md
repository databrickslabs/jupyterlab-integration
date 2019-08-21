# Local JupyterLab connecting to Databricks via SSH

This package allows to connect to a remote Databricks cluster from a locally running Jupyter Lab:

![Overview](docs/overview.png)

## 1 Prerequisites

### 1.1 Databricks CLI

Install Databricks CLI and configure profile(s) for your cluster(s)

- AWS: https://docs.databricks.com/user-guide/dev-tools/databricks-cli.html)
- Azure: https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html

**Note:** Whenever `$PROFILE` is used in this documentation, it refers to a valid Databricks CLI profile name, stored in a shell environment variable.

### 1.2 SSH keys

- Create an ssh key pair called `~/.ssh/id_$PROFILE` for each cluster
- Add the public key to the cluster SSH configuration

**Note:** Only clusters with valid ssh configuration can be accessed by *databrickslabs_jupyterlab*. This can also be done with *databrickslabs_jupyterlab*, see below

## 2 Installation

- Create a new conda environment and install *databrickslabs_jupyterlab* with the following commands:

    ```bash
    (base)$ conda create -n db-jlab python=3.6
    (base)$ conda activate db-jlab
    (base)$ pip install --upgrade databrickslabs-jupyterlab
    ```

- Bootstrap the environment for *databrickslabs_jupyterlab* with the following command:

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab -b
    ```

    It finishes with an overview of the usage.
    

## 3 Usage

### 3.1 Configure ssh access to the cluster

If the ssh connection with the cluster is not already configured, get the cluster ID from the cluster URL: 

Select menu entry *Clusters* and then click on the cluster of choice. The URL in the browser address window should look like:

- AWS: 
`https://$PROFILE.cloud.databricks.com/#/setting/clusters/$CLUSTER_ID/configuration`
- Azure: 
`https://$PROFILE.azuredatabricks.net/?o=$ORG_ID#/setting/clusters/$CLUSTER_ID/configuration`

and call:

```bash
(db-jlab)$ databrickslabs-jupyterlab $PROFILE -s -i $CLUSTER_ID
```

### 3.2 Starting Jupyter Lab

- Activate the conda environment for *databrickslabs-jupyterlab* with the following command:

    ```bash
    (base)$ conda activate db-jlab
    ```

- Create a jupyter kernel specification for a databricks cli profile ($PROFILE) with the following command:

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -k
    ```

- Start Jupyter Lab the usual way:

    ```bash
    (db-jlab)$ jupyter lab
    ```

    **Note:** A new kernel is available in the kernel change menu


### 3.3 Using Spark in the Notebook

#### Getting a remote Spark Session in the notebook

When the cluster is already running the status bar of Jupyter lab should show

![kernel ready](docs/connected.png)

To connect to the remote Spark context, enter the following two lines into a notebook cell:

```python
[1] from databrickslabs_jupyterlab.connect import dbcontext, is_remote
    dbcontext()
```

This will request you to add the token copied to clipboard above:

```text
    Fri Aug  9 09:58:04 2019 py4j imported
    Enter personal access token for profile 'demo' |_____________________________|
```

After pressing *Enter*, you will see

```text
    Gateway created for cluster '0806-143104-skirt84' ... connected
    The following global variables have been created:
    - spark       Spark session
    - sc          Spark context
    - sqlContext  Hive Context
    - dbutils     Databricks utilities
```

**Note:** `databrickslabs-jupyterlab $PROFILE -c` let's you quickly copy the token to the clipboard so that you can simply paste the token to the input box.

#### Restart after cluster auto-termination

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

#### Notebook hung after cluster start or kernel change

When this happens, usually the local Jupyter lab frontend and the remote kernel are out of sync. Try the following:

- Save your notebook(s) and refresh the browser page.
- If it still doesn't work, additionally restart the kernel

## 4 Creating a mirror of a remote Databricks cluster

For the specific use case when the same notebook should run locally and remotely, a local mirror of the remote libraries and versions is needed. This can be achieved with *databrickslabs_jupyterlab* with the following command:

```bash
$(base) conda activate db-jlab
$(db-jlab) databrickslabs-jupyterlab $PROFILE -m
```

It will 
- Ask for the cluster to mirror

    ```bash
    Valid version of conda detected: 4.7.11

    * Getting host and token from .databrickscfg

    * Select remote cluster
    [?] Which cluster to connect to?: 0: bernhard-5.5-ml (id: 0806-143104-skirt84, state: RUNNING, scale: 2-4)
    > 0: bernhard-5.5-ml (id: 0815-32415-abcde42, state: RUNNING, scale: 2-4)

    => Selected cluster: bernhard-5.5-ml (ec2-xxx-xxx-xxx-xxx.us-west-2.compute.amazonaws.com)
    ```

- Configure ssh access

    ```bash
    * Configuring ssh config for remote cluster
    => Added ssh config entry or modified IP address:

        Host 0815-32415-abcde42
            HostName ec2-xxx-xxx-xxx-xxx.us-west-2.compute.amazonaws.com
            User ubuntu
            Port 2200
            IdentityFile ~/.ssh/id_demo
            ServerAliveInterval 300

    => Testing whether cluster can be reached
    ```

- Retrieve the necessary libraries to install locally.

    ```bash
    * Installation of local environment to mirror a remote Databricks cluster

        Library versions being installed:
        - hyperopt==0.1.2
        - Keras==2.2.4
        - Keras-Applications==1.0.8
        - Keras-Preprocessing==1.1.0
        - matplotlib==2.2.2
        - mleap==0.8.1
        ...
        - tensorflow-estimator==1.13.0
        - torch==1.1.0
        - torchvision==0.3.0
    ```

- Ask for an environment name (default is the remote cluster name):

    ```bash
        => Provide a conda environment name (default = bernhard-5.5-ml):
    ```

- And finally installs the new environment:

    ```bash
    Installing conda environment bernhard-5.5-ml
    ...
    ```

After switching into this environment via

```bash
conda activate bernhard-5.5-ml
```

follow the usage guide in section 3.

## 5 Details

- **Show help**

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab -h

    usage: databrickslabs-jupyterlab [-h] [-b] [-m] [-c] [-f] [-i CLUSTER_ID] [-k]
                                 [-l] [-o ORGANISATION] [-p] [-r]
                                 [-v {all,diff,same}]
                                 [profile]

    Configure remote Databricks access with Jupyter Lab

    positional arguments:
    profile               A databricks-cli profile

    optional arguments:
    -h, --help            show this help message and exit
    -b, --bootstrap       Bootstrap the local databrickslabs-jupyterlab
                            environment
    -m, --mirror          Mirror a a remote Databricks environment
    -c, --clipboard       Copy the personal access token to the clipboard
    -f, --force           Force remote installation of databrickslabs_jupyterlab
                            package
    -i CLUSTER_ID, --id CLUSTER_ID
                            The cluster_id to avoid manual selection
    -k, --kernelspec      Create a kernel specification
    -l, --lab             Safely start Jupyter Lab
    -o ORGANISATION, --organisation ORGANISATION
                            The organisation for Azure Databricks
    -p, --profiles        Show all databricks cli profiles and check SSH key
    -r, --reconfigure     Reconfigure cluster with id cluster_id
    -v {all,diff,same}, --versioncheck {all,diff,same}
                            Check version of local env with remote env
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

- **Create jupyter kernel for remote cluster**

    - Databricks on AWS:

        ```bash
        (db-jlab)$ databrickslabs-jupyterlab $PROFILE -k [-i <cluster name>]
        ```

    - Azure:

        ```bash
        (db-jlab)$ databrickslabs-jupyterlab $PROFILE -k -o <organisation> [-i <cluster name>]
        ```

    This will execute the following steps:

    - Get host and token from `.databrickscfg` for the given profile
    - In case `-i` is not used, show a list of clusters that have the correct SSH key (id_$PROFILE) configured
    - Installs `databrickslabs_jupyterlab` and `ipywidgets` on the remote driver
    - Creates the remote kernel specification

- **Safely start Jupyter Lab**

    while you can start Jupyter Lab via `jupyter lab`, it is recommended to use the wrapper

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -l [-i <cluster name>]
    ```

    It will check whether the remote cluster is up and running, update the ssh info, check the availability of th relevant libs before starting jupyter Lab.

- **Copy Personal Access token for databricks workspace to the clipboard**

    This is the same command on AWS and Azure

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -c
    ```

- **Compare local and remote library versions (uses the locally activated canda environment)**

    ```bash
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -v all|same|diff [-i <cluster name>]
    ```

## 4 Test notebooks

To work with the test notebooks in `./examples` the remote cluster needs to have the following libraries installed:

- mlflow==1.0.0
- spark-sklearn
