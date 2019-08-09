#   Copyright 2019 Bernhard Walter
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import atexit
import base64
import configparser
import getpass
import os
import random
import sys
import time

from IPython.core.magic import line_magic, line_cell_magic
from IPython import get_ipython
from IPython.display import HTML, display

sys.path.insert(0, "/databricks/spark/python/lib/py4j-0.10.7-src.zip")
sys.path.insert(0, "/databricks/spark/python")
sys.path.insert(0, "/databricks/jars/spark--driver--spark--resources-resources.jar")

# will only work on the Databricks side
try:
    from pyspark.context import SparkContext
    from pyspark.conf import SparkConf
    from pyspark.sql import HiveContext

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from PythonShell import get_existing_gateway, RemoteContext  # pylint: disable=import-error

    from dbutils import DBUtils  # pylint: disable=import-error
except:
    pass

from databricks_jupyterlab.rest import Command, Context
from databricks_jupyterlab.progress import load_progressbar, load_css
from databricks_jupyterlab.dbfs import Dbfs
from databricks_jupyterlab.database import Databases
from databricks_jupyterlab.info import Info


class JobInfo():
    def __init__(self, pool_id):
        self.pool_id = pool_id
        self.group_id = None


def is_remote():
    return os.environ.get("DBJL_HOST", None) is not None


def is_azure():
    return os.environ.get("DBJL_ORG", None) is not None


def dbcontext(progressbar=True):
    ip = get_ipython()

    if not is_remote():
        return "This is not a remote Databricks kernel"

    spark = ip.user_ns.get("spark")
    if spark is not None:
        print("Spark context already exists")
        load_css()
        return spark

    # Get the configuration injected by the client
    #
    profile = os.environ.get("DBJL_PROFILE", None)
    host = os.environ.get("DBJL_HOST", None)
    clusterId = os.environ.get("DBJL_CLUSTER", None)
    organisation = os.environ.get("DBJL_ORG", None)
    # print("Databricks Host:", host)
    # print("Cluster Id:", clusterId)
    if organisation is not None:
        print("Organisation:", organisation)

    # Create a Databricks virtual python environment and start thew py4j gateway
    #
    token = getpass.getpass("\nEnter personal access token for profile '%s'" % profile)

    command = Command(url=host, clusterId=clusterId, token=token)
    print("Gateway created for cluster '%s' " % (clusterId), end="", flush=True)

    # Fetch auth_token and gateway port ...
    #
    cmd = 'c=sc._gateway.client.gateway_client; print(c.gateway_parameters.auth_token, c.port)'
    command.execute(cmd)

    result = command.status()

    while result["status"] != "Finished":
        time.sleep(1)
        print(".", end="", flush=True)
        result = command.status()

    auth_token, port = result["results"]["data"].split(" ")
    port = int(port)

    interpreter = "/databricks/python/bin/python"
    # Ensure that driver and executors use the same python
    #
    os.environ["PYSPARK_PYTHON"] = interpreter
    os.environ["PYSPARK_DRIVER_PYTHON"] = interpreter

    # ... and connect to this gateway
    #
    gateway = get_existing_gateway(port, True, auth_token)
    print(". connected")
    # print("Python interpreter: %s" % interpreter)

    # Retrieve spark session, sqlContext and sparkContext
    #
    conf = SparkConf(_jconf=gateway.entry_point.getSparkConf())
    sqlContext = RemoteContext(gateway=gateway, conf=conf)

    sqlContext = HiveContext(sqlContext, gateway.entry_point.getSQLContext())
    spark = sqlContext.sparkSession
    sc = spark.sparkContext

    # Enable pretty printing of dataframes
    #
    spark.conf.set("spark.sql.repl.eagerEval.enabled", "true")

    # Define a separate pool for the fair scheduler
    # Todo: Find a better way to store pool_id instead of this hack
    #
    job_info = JobInfo(str(random.getrandbits(64)))

    # Patch the remote spark UI into the _repr_html_ call
    #
    def repr_html(uiWebUrl):
        def sc_repr_html():
            return """
            <div>
                <p><b>SparkContext</b></p>
                <p><a href="{uiWebUrl}">Spark UI</a></p>
                <dl>
                  <dt>Version</dt><dd><code>v{sc.version}</code></dd>
                  <dt>AppName</dt><dd><code>{sc.appName}</code></dd>
                </dl>
            </div>
            """.format(sc=spark.sparkContext, uiWebUrl=uiWebUrl)

        return sc_repr_html

    if organisation is None:
        sparkUi = "%s#/setting/clusters/%s/sparkUi" % (host, clusterId)
    else:
        sparkUi = "%s/?o=%s#/setting/clusters/%s/sparkUi" % (host, organisation, clusterId)

    sc_repr_html = repr_html(sparkUi)
    sc._repr_html_ = sc_repr_html

    # Monkey patch Databricks Cli to allow mlflow tracking with the credentials provided
    # by this routine
    # Only necessary when mlflow is installed
    #
    try:
        from databricks_cli.configure.provider import ProfileConfigProvider, DatabricksConfig

        def get_config(self):
            config = DatabricksConfig(host, None, None, token, False)
            if config.is_valid:
                return config
            return None

        ProfileConfigProvider.get_config = get_config
    except:
        pass

    # Initialize the ipython shell with spark context
    #
    shell = get_ipython()
    shell.sc = sc
    shell.sqlContext = sqlContext
    shell.displayHTML = lambda html: display(HTML(html))

    # Retrieve the py4j gateway entrypoint
    #
    entry_point = spark.sparkContext._gateway.entry_point

    # Initialize dbutils
    #
    dbutils = DBUtils(shell, entry_point)

    # Setting up Spark progress bar
    #
    if progressbar:
        # print("Set up Spark progress bar")
        load_progressbar(ip, sc, job_info)
        load_css()

    # Register sql magic
    #
    ip.register_magic_function(sql, magic_kind='line_cell')

    # Ensure that the virtual python environment and py4j gateway gets shut down
    # when the python interpreter shuts down
    #
    def shutdown_kernel():
        from IPython import get_ipython
        ip = get_ipython()

        ip = get_ipython()
        if ip.user_ns.get("spark", None) is not None:
            del ip.user_ns["spark"]
        if ip.user_ns.get("sc", None) is not None:
            del ip.user_ns["sc"]
        if ip.user_ns.get("sqlContext", None) is not None:
            del ip.user_ns["sqlContext"]
        if ip.user_ns.get("dbutils", None) is not None:
            del ip.user_ns["dbutils"]

        # Context is a singleton
        Context().destroy()

    atexit.register(shutdown_kernel)

    # Forward spark variables to the user namespace
    #
    ip.user_ns["spark"] = spark
    ip.user_ns["sc"] = sc
    ip.user_ns["sqlContext"] = sqlContext
    ip.user_ns["dbutils"] = dbutils

    print("The following global variables have been created:")
    print("- spark       Spark session")
    print("- sc          Spark context")
    print("- sqlContext  Hive Context")
    print("- dbutils     Databricks utilities\n")
    print("")
    print("Open dbfs browser:     import databricks_jupyterlab as dj; dj.browse_dbfs(dbutils)")
    print("Open database browser: import databricks_jupyterlab as dj; dj.browse_databases(spark)")
    print("")

    return spark


@line_cell_magic
def sql(line, cell=None):
    ip = get_ipython()
    spark = ip.user_ns["spark"]
    if cell == None:
        code = line
    else:
        code = cell
    return spark.sql(code)
