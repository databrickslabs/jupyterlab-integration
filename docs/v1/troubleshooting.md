## Troubleshooting

- **The status bar at the bottom of Jupyter lab does not show** `...|Idle  [Connected]`

    - Check whether the cluster is running.
    - Check whether VPN is running, if necessary to connect to port 2200 of the cluster.
    - Check whether you can access the cluster from the command line.

        ```bash
        (db-jlab)$ ssh $CLUSTER_ID
        ```

    If this all is working successfully, then most probably the Jupyter kenrel mechnnism is out of sync. 
    **=> Solution:** Fully shut down the kernel in Jupyter and select the kernel again. This will execute all prerequisite checks and confgurations and the notebook should connect succesfully again.

- **The notebook does not work after kernel restart**

    Somtimes Jupyter fails to kill the remote kernel and the Jupyter kenrel mechanism gets out of sync. 
    **=> Solution:** Fully shut down the kernel in Jupyter and select the kernel again. This will execute all prerequisite checks and confgurations and the notebook should connect succesfully again.

- **Browsing DBFS or the databases does not work**

    When you click on entries one of the browsing windows and there is no response, then Juypter frontend is not fully in sync with the Jupyter backend.
    **=> Solution:**: Save the notebook and execute a browser refresh of the page. Afterwards the database and DBFS browser should work again (you need to open them again)
