### V1.0.x

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


