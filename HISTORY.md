### V2.2.0 (Apr 2021)

- **Jupyter Lab support** 
    With support for Jupyterlab the installation could be simplified drastically

- **Support of Databricks Runtimes 6.4 and higher (incl 8.1)**

### V2.1.0 (Jan 2021)

- **A new parser for ssh/config** 
    It aims for minimum changes (including whitespaces and comments). For verification it shows the diff view to the original version.

- **SSH tunnels**
    SSH tunnels are now supported by setting the environment variable SSH_TUNNEL to `address:port` of the tunnel service. See above where a standard AWS Databricks hostname and port (`ec2-11-22-33-44.eu-central-1.compute.amazonaws.com`, `2200`) got replaced by a SSH tunnel at `111.222.333.444` and port `2222`. 
    For the ssh tunnel one can use a managed service like [ngrok](https://ngrok.com/). 
    Alternatively, build your own tunneling service based on e.g. [Fast Reverse Proxy (fpr)](https://github.com/fatedier/frp) as described in ![Fast Reverse proxy configuration](docs/v2/frp.md).
    
- **Support of Databricks Runtimes 6.4 and higher (incl 7.5)**


### V2.0.0 (May 2020)

- **Input of Personal Access Token (PAT) in Jupyter is not necessary any more**

    While starting the kernel, the kernel manager will use an own kernel client and create the Spark Session and other artifacts via REST API and the secure SSH tunnels *[(DEMO)](docs/v2/news/start-kernelspec.md)*.

- **Native Windows support**

    Anaconda and Jupyter on Windows 10 (with OpenSSH) can be used with *JupyterLab Integration* *[(DEMO)](docs/v2/news/windows.md)*.

- **Docker support**

    No need for local Anaconda and *JupyterLab Integration* installation - the quickest way to test *JupyterLab Integration* *[(DEMO)](docs/v2/news/docker.md)*.

- **Browsers**

    - **DBFS browser with file preview**

        The DBFS browser does not use sidecar any more and allows to preview many text files like csv, sh, py, ... *[(DEMO)](docs/v2/news/dbfs-browser.md)*

    - **Database browser with schema and data preview**

        The Database browser does not use sidecar any more and allows to preview the table schema and shows sample rows of the data *[(DEMO)](docs/v2/news/database-browser.md)*

    - **MLflow browser**

        A mlflow experiements browser that converts all runs of an experiment into a Pandas Dataframe to query and compare best runs in pandas. *[(DEMO - Intro)](docs/v2/news/mlflow-browser-1.md)*, *[(DEMO - Keras)](docs/v2/news/mlflow-browser-2.md)*, *[(DEMO - MLlib)](docs/v2/news/mlflow-browser-3.md)*

- **dbutils**

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

- **Experimental features**

    - **Scala support (*experimental*)**

        The `%%scala` magic will send Scala code to the same Spark Context *[(DEMO)](docs/v2/news/scala-magic.md)*

    - **%fs support (*experimental*)**

        The `%fs` of `%%fs` magic is supported as a shortcut for `dbutils.fs.xxx` *[(DEMO)](docs/v2/news/fs-magic.md)*

### V1.0.x (December 2019)

- **Use *Databricks CLI* profiles and contain URLs and tokens**

    *Jupyterlab Integration* used officially supported *Databroicks CLI* configurations to retrieve the Personal Access Tokens and URLs for remote cluster access. Personal Access Tokens will not be copied to the remote cluster

- **Create and manage Jupyter kernel specifications for remote Databricks clusters**

    *Jupyterlab Integration* allows to create Jupyter kernel specifications for remote Databricks clusters via SSH. Kernel specifications can also be reconfigured or deleted

- **Configure SSH locally and remotely**

    *Jupyterlab Integration* allows to create a local ssh key pair and configure the cluster with the public key for SSH access. INjecting the public key will restart the remote cluster

- **Create a Spark session and attach notebooks to it**

    With *Jupyterlab Integration*, one needs to provide the Personal Access Token in th browser to authenticate the createion of a Spark Session. The current notebook will then be connected with this Spark session.

- **Mirror a a remote Databricks environment**

    *Jupyterlab Integration* can mirror the versions of Data Science related libraries to a local conda environment. A blacklist and a whitelist allow to control which libraries are actually mirrored


