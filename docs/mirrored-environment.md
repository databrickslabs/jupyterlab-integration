## 4 Creating a mirror of a remote Databricks cluster

For the specific use case when the same notebook should run locally and remotely, a local mirror of the remote libraries and versions is needed. There are two ways to achieve this:

- White list
    The packages mirrored are filtered via white list of Data Science focussed libraries (if the packages is installed on the remote cluster and is in the white list, it will be installed in the local mirror). The list can be printed with

    ```bash
    databrickslabs_jupyterlab -W
    ```

- Black list
    The packages mirrored are filtered via black list of generic libraries (if the packages is installed on the remote cluster and is in the white list, it will *not* be installed in the local mirror). The list can be printed with

    ```bash
    databrickslabs_jupyterlab -B
    ```

A local mirror can be created via *databrickslabs_jupyterlab* with the following command:

```bash
$(base) conda activate db-jlab
$(db-jlab) databrickslabs-jupyterlab $PROFILE -m     # filter via black list
# OR
$(db-jlab) databrickslabs-jupyterlab $PROFILE -m -w  # filter via white list
```

The command will

- ask for the cluster to mirror

    ```text
    Valid version of conda detected: 4.7.11

    * Getting host and token from .databrickscfg

    * Select remote cluster
    [?] Which cluster to connect to?: 0: bernhard-5.5-ml (id: 0806-143104-skirt84, state: RUNNING, scale: 2-4)
    > 0: bernhard-5.5-ml (id: 0815-32415-abcde42, state: RUNNING, scale: 2-4)

    => Selected cluster: bernhard-5.5-ml
    ```

- configure ssh access

    ```text
    * Configuring ssh config for remote cluster
    => Added ssh config entry or modified IP address:

        Host 0815-32415-abcde42
            HostName ec2-xxx-xxx-xxx-xxx.us-west-2.compute.amazonaws.com
            User ubuntu
            Port 2200
            IdentityFile ~/.ssh/id_demo
            ServerAliveInterval 5
            ServerAliveCountMax 2
            ConnectTimeout 5

    => Testing whether cluster can be reached
    ```

- retrieve the necessary libraries to install locally.

    ```text
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

- ask for an environment name (default is the remote cluster name):

    ```text
        => Provide a conda environment name (default = bernhard-5.5-ml):
    ```

- and finally install the new environment:

    ```text
    * Installing conda environment bernhard-5.5-ml
    ...
    ```

After switching into this environment via

```bash
(base)$ conda activate bernhard-5.5-ml
```

follow the usage guide in section 3 of the main [Readme](../README.md).