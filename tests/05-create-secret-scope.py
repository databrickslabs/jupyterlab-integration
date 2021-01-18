import sys

from databricks_cli.secrets.api import SecretApi

from databrickslabs_jupyterlab.remote import connect

from helpers import get_profile

profile = get_profile()

try:
    apiclient = connect(profile)
    client = SecretApi(apiclient)
except Exception as ex:  # pylint: disable=broad-except
    print(ex)
    sys.exit(1)

client.create_scope("dbjl-pytest", None, None, None)
client.put_secret("dbjl-pytest", "pytest-key", "databrickslabs-jupyterlab", None)
