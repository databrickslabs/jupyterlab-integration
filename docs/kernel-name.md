## Kernel names

The *databrickslabs_jupyterlab* kernel names have the following structure:

`SSH $CLUSTER_ID $PROFILE:$CLUSTER_NAME ($LOCAL_CONDA_ENV_NAME)`

where `$LOCAL_CONDA_ENV_NAME` will be omitted if `$LOCAL_CONDA_ENV_NAME` == `$CLUSTER_NAME`.

Example if local conda environment name is different from Databricks cluster name:

- `SSH 0806-143104-skirt84 demo:bernhard-5.5-ml (db-jlab)`

    - Workspace profile name: `demo`
    - Cluster ID: `0806-143104-skirt84`
    - Cluster Name: `bernhard-5.5-ml`
    - Local conda environment: `db-jlab`

Example if local conda environment name equals the Databricks cluster name:

- `SSH 0806-143104-skirt84 demo:bernhard-5.5-ml`

    - Workspace profile name: `demo`
    - Cluster ID: `0806-143104-skirt84`
    - Cluster Name: `bernhard-5.5-ml`
    - Local conda environment: `bernhard-5.5-ml`