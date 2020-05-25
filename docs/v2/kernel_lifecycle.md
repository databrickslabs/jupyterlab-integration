## 5.1 Kernel Lifecycle

### 5.1.1 Switching kernels

Kernels can be switched via the Jupyterlab Kernel Change dialog. However, when switching to a remote kernel, the local connection context might get out of sync and the notebook cannot be used. In this case:

1. Shutdown the kernel
2. Select the remote kernel again from the Jupyterlab Kernel Change dialog. 

A simple Kernel Restart by Jupyter lab will not work since this does not refresh the connection context!

### 5.1.2 Restart after cluster auto-termination

Should the cluster auto terminate while the notebook is connected or the network connection is down, the status bar will change to

- ![kernel disconnected](cluster_unreachable.png)

Additionally a dialog to confirm that the remote cluster should be started again will be launched in JupyterLab:

![running with Spark](restart-dialog.png)

Notes: 

- One can check connectivity before, e.g. by calling `ssh <cluster_id>` in a terminal window)
- After cancelling the dialog, clicking on the status bar entry as indicated by the message will open the dialog box again.

During restart the following status messages will be shown in this order:

- Starting 
    ![cluster-starting](cluster_starting-1.png)
- Starting
    ![cluster-starting](cluster_starting_5.png)
- Configuring SSH
    ![configure-ssh](configuring_ssh.png)
- Installing cluster libraries
    ![installing-cluster-libs](installing_cluster_libraries.png)
- Installing driver libraries
    ![installing-driver-libs](installing_driver_libs.png)
- Successfully connected to kernel
    ![connected](connect_idle.png)
- Successfully running
    ![running](connect_running.png)
- Successfully running with Spark
    ![running with Spark](connect_running_spark.png)

### 5.1.3 Reconfiguring the cluster

If the cluster was restarted and the frontend did not recognize the restart, Clicking on the `[Running]` or `[Running(Spark)]` entry in the status bar of JupyterLab will raise the following dialog box:

- ![kernel disconnected](reconfigure.png)

This will repeat the steps

- Configuring SSH
    ![configure-ssh](configuring_ssh.png)
- Installing driver libraries
    ![installing-driver-libs](installing_driver_libs.png)
