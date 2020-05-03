import json
import sys
import os

import yaml

from databricks_cli.clusters.api import ClusterApi

from databrickslabs_jupyterlab.remote import connect


def delete_cluster(client, cluster_id):
    try:
        response = client.permanent_delete(cluster_id)
        return response
    except Exception as ex:  # pylint: disable=broad-except
        print(ex)
        return None


with open("/tmp/running_clusters.json", "r") as fd:
    clusters = json.load(fd)

config = yaml.safe_load(open("clusters.yaml", "r"))
profile = config["profile"]

try:
    apiclient = connect(profile)
    client = ClusterApi(apiclient)
except Exception as ex:  # pylint: disable=broad-except
    print(ex)
    sys.exit(1)


for name, cluster_id in clusters.items():
    print(name)
    delete_cluster(client, cluster_id)

os.unlink("/tmp/running_clusters.json")
