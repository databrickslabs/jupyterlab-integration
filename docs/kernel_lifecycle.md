## 1 Kernel Lifecycle

### 1.1 Switching kernels

Kernels can be switched via the Jupyterlab Kernel Change dialog. However, when switching to a remote kernel, the local connection context might get out of sync and the notebook cannot be used. In this case:

1. shutdown the kernel
2. Select the remote kernel again from the Jupyterlab Kernel Change dialog. 

A simple Kernel Restart by Jupyter lab will not work since this does not refresh the connection context!


### 1.2 Restart after cluster auto-termination

Should the cluster auto terminate while the notebook is connected or the network connection is down, the status bar will change to

- ![kernel disconnected](cluster-unreachable.png)

Additionally a dialog to confirm that the remote cluster should be started again will be launched in Jupyter Lab 

Notes: 

- One can check connectivity before, e.g. by calling `ssh <cluster_id>` in a terminal window)
- After cancelling the dialog, clicking on the status bar entry as indicated by the message will open the dialog box again

During restart the following status messages will be shown in this order:

- ![cluster-starting](cluster-starting.png)
- ![installing-cluster-libs](installing-cluster-libs.png)
- ![installing-driver-libs](installing-driver-libs.png)
- ![configure-ssh](configure-ssh.png)
- ![starting](starting.png)

After successful start the status would again show:

- ![kernel ready](connected.png)