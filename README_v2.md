# Local JupyterLab connecting to Databricks via SSH

This package allows to connect to a remote Databricks cluster from a locally running JupyterLab.


                                    ______________________________________
                              _____|                                      |_____
                              \    |    NEW MAJOR RELEASE V2 (May 2020)   |    /
                               )   |______________________________________|   (
                              /______)                                  (______\

**New features:**

- **Input of Personal Access Token (PAT) in Jupyter is not necessary any more**

    While starting the kernel, the kernel manager will use an own kernel client and create the Spark Session and other artifacts via REST API and the secure SSH tunnels *[(DEMO)](docs/v2/news/start-kernelspec.md)*.

- **Native Windows support**

    Anaconda and Jupyter on Windows 10 (with OpenSSH) can be used with *JupyterLab Integration*

- **Docker support**

    No need for local Anaconda and *JupyterLab Integration* installation - the quickest way to test *JupyterLab Integration*.

- **DBFS browser with file preview**

    The DBFS browser does not use sidecar any more and allows to preview many text files like csv, sh, py, ... *[(DEMO)](docs/v2/news/dbfs-browser.md)*

- **Database browser with schema and data preview**

    The Database browser does not use sidecar any more and allows to preview the table schema and shows sample rows of the data *[(DEMO)](docs/v2/news/database-browser.md)*

- **Support for `dbutils.secrets`**

    `dbutils.secrets` allow to hide credentials from your code *[(DEMO)](docs/v2/news/dbutils.secrets.md)*

- **Support for `dbutils.notebook`**

    Higher compatibility with Databricks notebooks: 
    - `dbutils.notebook.exit` stops "Running all cells" *[(DEMO)](docs/v2/news/dbutils.notebook.exit.md)* 
    - `dbutils.notebook.run` allows to run `.py`and `.ipynb` files from notebooks in JupyterLab Integration *[(DEMO)](docs/v2/news/dbutils.notebook.run.md)*

- **Support for kernels without Spark**

    Create a *JupyterLab Integration* kernel specification with `--nospark` if no Spark Session on the remote cluster is required, e.g. for Deep Learning *[(DEMO)](docs/v2/news/with-and-without-spark.md)*

- **Support of Databricks Runtimes 6.4 and higher (incl 7.0)**

    The changed initialisation from DBR 6.4 and above (*pinned* mode) is now supported

- **JupyterLab 2.1 is now default**

    Bumped JupyterLab to the latest version

**New experimental features**

- **Scala support (*experimental*)**

    The `%%scala` magic will send Scala code to the same Spark Context *[(DEMO)](docs/v2/news/scala-magic.md)*

- **%fs support (*experimental*)**

    The `%fs` of `%%fs` magic is supported as a shortcut for `dbutils.fs.xxx` *[(DEMO)](docs/v2/news/fs-magic.md)*

- **Improved Databricks example notebook download from the Databricks documentation (*experimental*)**

    Supports downloading *.html* notebooks from the Databricks documentation web pages. Databricks magics like `%sh`, `%scala`, `%sql`, ... will be properly translated to Jupyter magics `%%sh`, `%%scala`, `%%sql`, ...

## 1 Prerequisites

1. **Operating System**

    macOS, Linux and Windows 10 (with OpenSSH)

2. **Anaconda installation**

    - A recent version of [Anaconda](https://www.anaconda.com/distribution) with Python >= *3.6*
    - Since *Jupyterlab Integration* will create a separate conda environment, [Miniconda](https://docs.conda.io/en/latest/miniconda.html) is sufficient to start
    - The tool *conda* must be newer than *4.7.5*, test were executed with *4.8.x*.

3. **Python**

    - Python 3.6 and Python 3.7 both on the remote cluster and locally (only for *DBR 5.5 LTS* Python 3.5 should be used locally).
    - Python 2.7 is not supported, neither on the remote cluster nor locally


4. **Databricks CLI**

    To install Databricks CLI and configure profile(s) for your cluster(s), please refer to [AWS](https://docs.databricks.com/user-guide/dev-tools/databricks-cli.html) / [Azure](https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html)

    Note: 

    - JupyterLab Integration does not support Databricks CLI profile with username password. Only [Personal Access Tokens](https://docs.databricks.com/dev-tools/api/latest/authentication.html) are supported.
    - Whenever `$PROFILE` is used in this documentation, it refers to a valid Databricks CLI profile name, stored in a shell environment variable.

5. **SSH access to the Databricks cluster**

    Configure your Databricks clusters to allow ssh access, see [Configure SSH access](docs/ssh-configurations.md)

    Note: 

    - *Only clusters with valid ssh configuration are visible to* `databrickslabs_jupyterlab`.

6. **Databricks Runtime**

    The project has been tested with Databricks runtimes on AWS and Azure for both MacOS and Windows client:

    - 5.5 LTS * / 5.5 ML LTS
    - 6.3 / 6.3 ML
    - 6.4 / 6.4 ML 
    - 6.5 / 6.5 ML
    - 7.0 BETA, 7.0 ML BETA 

    \* *not supported with Windows client due to conflicts with Python 3.5*

## 2 Running with docker

A docker image ready for working with *Jupyterlab Integration* is available from Dockerhub. There are two scripts in the folder `docker`:

- *databrickslabs-jupyterlab* for docker (`docker/dk-dj`):

    This is the *Jupyterlab Integration* configuration utility using the docker image:

    ```bash
    docker run -it --rm \
        -p 8888:8888 \
        -v $(pwd)/kernels:/home/dbuser/.local/share/jupyter/kernels/ \
        -v $HOME/.ssh/:/home/dbuser/.ssh  \
        -v $HOME/.databrickscfg:/home/dbuser/.databrickscfg \
        -v $(pwd):/home/dbuser/notebooks \
        bwalter42/databrickslabs_jupyterlab:2.0.0-rc2 \
        /opt/conda/bin/databrickslabs-jupyterlab $@
    ```

- *jupyter* for docker (`docker/dk-jupyter`):

    Allows to run *jupyter* commands using the docker image:

    ```bash
    docker run -it --rm \
        -p 8888:8888 \
        -v $(pwd)/kernels:/home/dbuser/.local/share/jupyter/kernels/ \
        -v $HOME/.ssh/:/home/dbuser/.ssh  \
        -v $HOME/.databrickscfg:/home/dbuser/.databrickscfg \
        -v $(pwd):/home/dbuser/notebooks \
        bwalter42/databrickslabs_jupyterlab:2.0.0-rc2 \
        /opt/conda/bin/jupyter $@
    ```

The two scripts assume that notebooks will be in the current folder and kernels will be in the `kernels` subfolder of the current folder:

```text
$PWD  <= Start jupyterLab from here
 |_ kernels
 |  |_ <Jupyterlab Integration kernel spec>
 |  |_ ... 
 |_ project
 |  |_ notebook.ipynb
 |_ notebook.ipynb
 |_ ...
```

Notes:

- If you keep the defaults in the two scripts, create a folder `./kernels` in your working directory before running.
- **The two scripts will modify your ~/.ssh/config and ~/.ssh/know_hosts**:
If you you do not want this to happen, you can for example extend the folder structure to

    ```text
    $PWD  <= Start jupyterLab from here
    |_ .ssh                      <= new
    |  |_ config                 <= new
    |  |_ id_$PROFILE            <= new
    |  |_ id_$PROFILE.pub        <= new
    |_ kernels
    |  |_ <Jupyterlab Integration kernel spec>
    |  |_ ... 
    |_ project
    |  |_ notebook.ipynb
    |_ notebook.ipynb
    |_ ...
    ```

     create the necessary public/private key pair in `$(pwd)/.ssh` and change the parameter `-v $HOME/.ssh/:/home/dbuser/.ssh` to  `-v $(pwd)/.ssh/:/home/dbuser/.ssh` in both commands.

- The scripts can be easily edited, used via alias or ported to Windows.

## 3 Local installation

1. **Install databrickslabs_jupyterlab**

    Create a new conda environment and install *databrickslabs_jupyterlab* with the following commands:

    ```bash
    (base)$ conda create -n db-jlab python=3.7
    (base)$ conda activate db-jlab
    (db-jlab)$ pip install --upgrade databrickslabs-jupyterlab==2.0.0-rc2
    ```

    The prefix `(db-jlab)$` for all command examples in this document assumes that the conda enviromnent `db-jlab` is activated.

2. **The tool databrickslabs_jupyterlab**

    It comes with a batch file `dj.bat` for Windows. On MacOS or Linux, an alias is recommended

    ```bash
    alias dj=databrickslabs_jupyterlab
    ```

    The following description will assume, this alias is set so that Windows, macOS and Linux share the same commands.

3. **Bootstrap databrickslabs_jupyterlab**

    Bootstrap the environment for *Jupyterlab Integration* with the following command (which will show the usage after successfully configuring *Juypterlab Integration*):

    ```bash
    (db-jlab)$ dj -b
    ```

## 4 Getting started with local installation or docker

Ensure, ssh access is correctly configured, see [Configure SSH access](docs/ssh-configurations.md)
If you work with the docker variant, use `dk-dj` instead of `dj` and `dk-jupyter` instead of `jupyter`.

### 4.1 Starting JupyterLab

1. **Create a kernel specification**
    In the terminal, create a jupyter kernel specification for a *Databricks CLI* profile `$PROFILE` and start JupyterLab with the following command:

    ```bash
    (db-jlab)$ dj $PROFILE -k
    ```

    A new kernel is available in the kernel change menu (see [here](docs/v2/kernel-name.md) for an explanation of the kernel name structure)

2. **Start JupyterLab**
    Start JupyterLab using *databrickslabs-jupyterlab*

    ```bash
    (db-jlab)$ dj $PROFILE -l
    ```

    The command with `-l` is a safe version for the standard command to start JupyterLab (`jupyter lab`) that ensures that the kernel specificiation is updated.

    

### 4.2 Using Spark in the Notebook

1. **Check whether the notebook is properly connected**

    When the notebook connected successfully to the cluster, the status bar at the bottom of JupyterLab should show 
    
    ![kernel ready](docs/v2/connect_running_spark.png)

    if you use a kernel with *Spark*, else just

    ![kernel ready](docs/v2/connect_running.png)

    If this is not the case, see [Troubleshooting](docs/v2/troubleshooting.md)

2. **Test the Spark access**

    To check the remote Spark connection, enter the following lines into a notebook cell:

    ```python
    import socket
    
    from databrickslabs_jupyterlab import is_remote
    
    result = sc.range(10000).repartition(100).map(lambda x: x).sum()
    print(socket.gethostname(), is_remote())
    print(result)
    ```

    It will show that the kernel is actually running remotely and the hostname of the driver. The second part quickly smoke tests a Spark job.

    ![Spark test](docs/v2/spark_result.png)

**Success:** Your local JupyterLab is successfully contected to the remote Databricks cluster

## 5 Advanced topics

[5.1 Switching kernels and restart after cluster auto-termination](docs/v2/kernel_lifecycle.md)

[5.2 Creating a mirror of a remote Databricks cluster](docs/v2/mirrored-environment.md)

[5.3 Detailed databrickslabs_jupyterlab command overview](docs/v2/details.md)

[5.4 How it works](docs/v2/how-it-works.md)

[5.5 Troubleshooting](docs/v2/troubleshooting.md)


## 6 Project Support
Please note that all projects in the /databrickslabs github account are provided for your exploration only, and are not formally supported by Databricks with Service Level Agreements (SLAs). They are provided AS-IS and we do not make any guarantees of any kind. Please do not submit a support ticket relating to any issues arising from the use of these projects.

Any issues discovered through the use of this project should be filed as GitHub Issues on the Repo. They will be reviewed as time permits, but there are no formal SLAs for support.

## 7 Test notebooks

To work with the test notebooks in `./examples` the remote cluster needs to have the following libraries installed:

- mlflow==1.x
- spark-sklearn
