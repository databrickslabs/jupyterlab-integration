## Configure SSH access

Configuring the SSH access comprises of 2 steps

1. **Workspace configuration**: This is usually done by an admin.
2. **Cluster configuration**: This can be done by any user who has the right to edit cluster configurations in Databricks.

The process is different for AWS and Azure and is describe in the following sections


### AWS

To understand SSH access to and configure Databricks clusters for SSH, please refer to [SSH Access to an AWS Databricks cluster](https://docs.databricks.com/user-guide/clusters/ssh.html#ssh-access-to-clusters). It describes the following two steps:

1. The **workspace configuration** step is only to open port 2200 in the security group.
2. The **cluster configuration** includes creating an ssh key pair and adding it to the cluster configuration of the Databricks cluster to be accessed.

The 2nd step (cluster configuration) can also be done using the *databrickslabs_jupyterlab* command from the command line:

- Get the cluster ID from the cluster URL: Select menu entry *Clusters* and then click on the cluster of choice. The URL in the browser address bar should look like:

    ```text
    https://$WORKSPACE.cloud.databricks.com/#/setting/clusters/$CLUSTER_ID/configuration
    ```

- Configure the ssh access

    ```bash
    (db-jlab)$ dj $PROFILE -s -i $CLUSTER_ID
    ```

### Azure

1. The **workspace configuration** on Azure is more complicated. It involves the following two steps:

    - For Azure Databricks you need to have an *Azure Databricks* cluster that is deployed into your own *Azure Virtual Network* (see [VNet Injection](https://docs.azuredatabricks.net/administration-guide/cloud-configurations/azure/vnet-inject.html)).
    - Additionally open port 2200 in the Network Security Group of your workspace.

    These tasks can usually only be executed by your Azure admin.

2. The **cluster configuration** includes creating an ssh key pair and adding it to the cluster configuration of the Databricks cluster to be accessed. You cann follow these steps in the [AWS documentation](https://docs.databricks.com/user-guide/clusters/ssh.html#ssh-access-to-clusters)

The 2nd step (cluster configuration) can also be done using the *databrickslabs_jupyterlab* command from the command line:

- Get the cluster ID from the cluster URL: Select menu entry *Clusters* and then click on the cluster of choice. The URL in the browser address bar should look like:

    ```text
    https://$REGION.azuredatabricks.net/?o=$ORG_ID#/setting/clusters/$CLUSTER_ID/configuration
    ```

- Configure the ssh access

    ```bash
    (db-jlab)$ dj $PROFILE -s -i $CLUSTER_ID
    ```
