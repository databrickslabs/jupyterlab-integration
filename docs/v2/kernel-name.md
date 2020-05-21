## Kernel names

The *databrickslabs_jupyterlab* kernel names have the following structure:

`SSH $CLUSTER_ID $PROFILE:$CLUSTER_NAME ($LOCAL_CONDA_ENV_NAME[/Spark])`

where `$LOCAL_CONDA_ENV_NAME` will be omitted if `$LOCAL_CONDA_ENV_NAME` == `$CLUSTER_NAME`.

Example if local conda environment name is different from Databricks cluster name:

- `SSH 0508-164224-fores138 demo:test-6.5-ml (db-jlab)`
- `SSH 0508-164224-fores138 demo:test-6.5-ml (db-jlab/Spark)`

    - Workspace profile name: `demo`
    - Cluster ID: `0508-164224-fores138`
    - Cluster Name: `test-6.5-ml`
    - Local conda environment: `db-jlab`
    - If Spark is used (`dj -k` without `--no-spark`): `/Spark`

Example if local conda environment name equals the Databricks cluster name:

- `SSH 0508-164224-fores138 demo:test-6.5-ml`
- `SSH 0508-164224-fores138 demo:test-6.5-ml (Spark)`

    - Workspace profile name: `demo`
    - Cluster ID: `0508-164224-fores138`
    - Cluster Name: `test-6.5-ml`
    - Local conda environment: `test-6.5-ml` (not visible in kernel name)
    - If Spark is used (`dj -k` without `--no-spark`): `(Spark)`
