import yaml
import sys

from databricks_cli.secrets.api import SecretApi

from databrickslabs_jupyterlab.local import get_db_config
from databrickslabs_jupyterlab.remote import connect

config = yaml.safe_load(open("clusters.yaml", "r"))
profile = config["profile"]

try:
    apiclient = connect(profile)
    client = SecretApi(apiclient)
except Exception as ex:  # pylint: disable=broad-except
    print(ex)
    sys.exit(1)

client.create_scope("dbjl-pytest", None)
client.put_secret("dbjl-pytest", "pytest-key", "databrickslabs-jupyterlab", None)
