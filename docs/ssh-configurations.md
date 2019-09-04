## Configure SSH access

To understand SSH access to and configure Databricks clusters for SSH, please refer to:

- **Workspace and cluster configuration for AWS:**

    [SSH Access to the cluster](https://docs.databricks.com/user-guide/clusters/ssh.html#ssh-access-to-clusters)

- **Workspace configuration for Azure:**

    - You need to have a *Azure Databricks* cluster that is deployed into your own *Azure Virtual Network* (see [VNet Injection](https://docs.azuredatabricks.net/administration-guide/cloud-configurations/azure/vnet-inject.html)). 
    - Additionally open port 2200 in the Network Security Group of your workspace.

- **Cluster configuration for Azure:**

    - For the cluster configuration then follow the steps in the AWS guide above

The cluster configuration part can also be accomplished with *databickslabs_jupyterlab*. This is especially helpful after creation of new clusters in an SSH enabled workspace:

- **Get the cluster ID from the cluster URL:**

    Select menu entry *Clusters* and then click on the cluster of choice. The URL in the browser address window should look like:

    - AWS: 
    `https://$PROFILE.cloud.databricks.com/#/setting/clusters/$CLUSTER_ID/configuration`
    - Azure: 
    `https://$PROFILE.azuredatabricks.net/?o=$ORG_ID#/setting/clusters/$CLUSTER_ID/configuration`

- **Use the command line tool to do the configuration:**

    ```bash
    (base)$ conda activate db-jlab
    (db-jlab)$ databrickslabs-jupyterlab $PROFILE -s -i $CLUSTER_ID
    ```
