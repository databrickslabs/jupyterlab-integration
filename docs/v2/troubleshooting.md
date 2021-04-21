## 7.5 Troubleshooting

- **The status bar at the bottom of Jupyter lab does not show** `...|Idle  [Running]` or `...|Idle  [Running(Spark)]`

    - Check whether the cluster is running.
    - Check whether VPN is running, if necessary to connect to port 2200 of the cluster.
    - Check whether you can access the cluster from the command line.

        ```bash
        (db-jlab)$ ssh $CLUSTER_ID
        ```

    If this all is working successfully, then most probably the Jupyter kenrel mechnnism is out of sync. 
    **=> Solution:** Fully shut down the kernel in Jupyter and select the kernel again. This will execute all prerequisite checks and confgurations and the notebook should connect succesfully again.

- **The notebook does not work after kernel restart**

    Somtimes Jupyter fails to kill the remote kernel and the Jupyter kernel mechanism gets out of sync. 
    **=> Solution:** Fully shut down the kernel in Jupyter and select the kernel again. This will execute all prerequisite checks and confgurations and the notebook should connect succesfully again.

- **Status is not show, progess bars are missing**

    Check that the following extensions are installed and enabled and OK:

    ```bash
    (dj) $ jupyter lab extension list
    
    Config dir: /Users/bernhard.walter/.jupyter

    Config dir: /opt/miniconda/envs/dj/etc/jupyter
        databrickslabs_jupyterlab enabled
        - Validating databrickslabs_jupyterlab...
        databrickslabs_jupyterlab 2.2.0 OK
        jupyterlab enabled
        - Validating jupyterlab...
        jupyterlab 3.0.14 OK
        nbclassic enabled
        - Validating nbclassic...
        nbclassic  OK
        ssh_ipykernel enabled
        - Validating ssh_ipykernel...
        ssh_ipykernel 1.2.1 OK

    Config dir: /usr/local/etc/jupyter
    ```

    ```bash
    (dj) $ jupyter server extension list

    Config dir: /Users/bernhard.walter/.jupyter

    Config dir: /opt/miniconda/envs/dj/etc/jupyter
        databrickslabs_jupyterlab enabled
        - Validating databrickslabs_jupyterlab...
        databrickslabs_jupyterlab 2.2.0 OK
        jupyterlab enabled
        - Validating jupyterlab...
        jupyterlab 3.0.14 OK
        nbclassic enabled
        - Validating nbclassic...
        nbclassic  OK
        ssh_ipykernel enabled
        - Validating ssh_ipykernel...
        ssh_ipykernel 1.2.1 OK

    Config dir: /usr/local/etc/jupyter
    ```

    If not, create a new conda environment and reinstall `databrickslabs-jupyterlab[cli]`