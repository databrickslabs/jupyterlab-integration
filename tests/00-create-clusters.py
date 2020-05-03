import json
from os.path import expanduser
import random
import sys

import yaml

from databricks_cli.clusters.api import ClusterApi

from databrickslabs_jupyterlab.local import get_db_config
from databrickslabs_jupyterlab.remote import connect


AUTOSCALE_CLUSTER = {
    "autoscale": {"min_workers": 2, "max_workers": 3},
    "cluster_name": "__dummy-to-be-replaced__",
    "spark_version": "__dummy-to-be-replaced__",
    "spark_conf": {},
    "node_type_id": "i3.xlarge",
    "driver_node_type_id": "i3.xlarge",
    "ssh_public_keys": ["__dummy-to-be-replaced__"],
    "custom_tags": {},
    "spark_env_vars": {"PYSPARK_PYTHON": "/databricks/python3/bin/python3"},
    "autotermination_minutes": 120,
    "init_scripts": [],
}

FIXED_CLUSTER = {
    "num_workers": 2,
    "cluster_name": "__dummy-to-be-replaced__",
    "spark_version": "__dummy-to-be-replaced__",
    "spark_conf": {},
    "node_type_id": "i3.xlarge",
    "driver_node_type_id": "i3.xlarge",
    "ssh_public_keys": ["__dummy-to-be-replaced__"],
    "custom_tags": {},
    "spark_env_vars": {"PYSPARK_PYTHON": "/databricks/python3/bin/python3"},
    "autotermination_minutes": 120,
    "init_scripts": [],
}


def create_cluster(client, cluster_conf):
    try:
        response = client.create_cluster(cluster_conf)
        return response
    except Exception as ex:  # pylint: disable=broad-except
        print(ex)
        return None


config = yaml.safe_load(open("clusters.yaml", "r"))
profile = config["profile"]
spark_versions = config["spark_versions"]
host, token = get_db_config(profile)
ssh_key = open(expanduser("~/.ssh/id_{}.pub".format(profile))).read()

try:
    apiclient = connect(profile)
    client = ClusterApi(apiclient)
except Exception as ex:  # pylint: disable=broad-except
    print(ex)
    sys.exit(1)


random.seed(42)

cluster_ids = {}

for spark_version in spark_versions:

    if random.random() < 0.5:
        cluster_conf = AUTOSCALE_CLUSTER.copy()
    else:
        cluster_conf = FIXED_CLUSTER.copy()

    cluster_conf["spark_version"] = spark_version
    cluster_conf["cluster_name"] = "TEST-" + spark_version.split("-scala")[0]
    cluster_conf["ssh_public_keys"] = [ssh_key]

    print(cluster_conf["cluster_name"])
    result = create_cluster(client, cluster_conf)
    cluster_ids[cluster_conf["cluster_name"]] = result["cluster_id"]

with open("/tmp/running_clusters.json", "w") as fd:
    fd.write(json.dumps(cluster_ids))
