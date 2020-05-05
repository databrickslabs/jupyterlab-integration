import sys

from databricks_cli.clusters.api import ClusterApi

from databrickslabs_jupyterlab.remote import connect

from helpers import get_profile, get_running_clusters


def restart_cluster(client, cluster_id):
    try:
        response = client.restart_cluster(cluster_id)
        return response
    except Exception as ex:  # pylint: disable=broad-except
        print(ex)
        return None


clusters = get_running_clusters()
profile = get_profile()

try:
    apiclient = connect(profile)
    client = ClusterApi(apiclient)
except Exception as ex:  # pylint: disable=broad-except
    print(ex)
    sys.exit(1)


for name, cluster_id in clusters.items():
    print(name)
    restart_cluster(client, cluster_id)
