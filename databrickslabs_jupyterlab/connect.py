import atexit
import base64
import configparser
import getpass
import io
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
        # Suppress py4j loading message on stderr by redirecting sys.stderr
        stderr_orig = sys.stderr
        sys.stderr = io.StringIO()
        from PythonShell import get_existing_gateway, RemoteContext  # pylint: disable=import-error
        out = sys.stderr.getvalue()
        # Restore sys.stderr
        sys.stderr = stderr_orig
        # Print any other error message to stderr
        if not "py4j imported" in out:
            print(out, file=sys.stderr)

    from dbutils import DBUtils  # pylint: disable=import-error
except:
    pass

from databrickslabs_jupyterlab.rest import Command, DatabricksApiException
from databrickslabs_jupyterlab.progress import load_progressbar, load_css
from databrickslabs_jupyterlab.dbfs import Dbfs
from databrickslabs_jupyterlab.database import Databases


class JobInfo():
    """Job info class for Spark jobs
    Args:
        pool_id (str): Pool ID to separate Spark jobs from each other
        group_id (str): Group ID to enable killing jobs and progress bar
    """
    def __init__(self, pool_id):
        self.pool_id = pool_id
        self.group_id = None


class DatabricksBrowser:
    """[summary]
    Args:
        spark (SparkSession): Spark Session object
        dbutils (DBUtils): DbUtils object
    """
    def __init__(self, spark, dbutils):
        self.spark = spark
        self.dbutils = dbutils

    def dbfs(self):
        """Start dbfs browser"""
        Dbfs(self.dbutils).create()

    def databases(self):
        """Start Database browser"""
        Databases(self.spark).create()


def is_remote():
    """Check whether the current context is on the remote cluster
    
    Returns:
        bool: True if remote else False
    """
    return os.environ.get("DBJL_HOST", None) is not None


def is_azure():
    """Check whether the current context is on Azure Databricks
    
    Returns:
        bool: True if Azure Databricks else False
    """
    return os.environ.get("DBJL_ORG", None) is not None


def dbcontext(progressbar=True):
    """Create a databricks context
    The following objects will be created
    - Spark Session
    - Spark Context
    - Spark Hive Context
    - DBUtils (fs module only)
    
    Args:
        progressbar (bool, optional): If True the spark progressbar will be installed. Defaults to True.
    """
    def get_sparkui_url(host, organisation, clusterId):
        if organisation is None:
            sparkUi = "%s#/setting/clusters/%s/sparkUi" % (host, clusterId)
        else:
            sparkUi = "%s/?o=%s#/setting/clusters/%s/sparkUi" % (host, organisation, clusterId)
        return sparkUi

    def show_status(spark, sparkUi):
        output = """
        <div>
            <dl>
            <dt>Spark Version</dt><dd>{sc.version}</dd>
            <dt>Spark Application</dt><dd>{sc.appName}</dd>
            <dt>Spark UI</dt><dd><a href="{sparkUi}">go to ...</a></dd>
            </dl>
        </div>
        """.format(sc=spark.sparkContext,
                   sparkUi=get_sparkui_url(host, organisation, clusterId),
                   num_executors=len(spark.sparkContext._jsc.sc().statusTracker().getExecutorInfos()))
        display(HTML(output))

    # Get the configuration injected by the client
    #
    profile = os.environ.get("DBJL_PROFILE", None)
    host = os.environ.get("DBJL_HOST", None)
    clusterId = os.environ.get("DBJL_CLUSTER", None)
    organisation = os.environ.get("DBJL_ORG", None)

    sparkUi = get_sparkui_url(host, organisation, clusterId)

    if not is_remote():
        return "This is not a remote Databricks kernel"

    ip = get_ipython()
    spark = ip.user_ns.get("spark")
    if spark is not None:
        print("Spark context already exists")
        load_css()
        show_status(spark, sparkUi)
        return None

    # Create a Databricks virtual python environment and start thew py4j gateway
    #
    token = getpass.getpass("Creating a Spark execution context:\nEnter personal access token for profile '%s'" % profile)

    try:
        command = Command(url=host, cluster_id=clusterId, token=token)
    except DatabricksApiException as ex:
        print(ex)
        return None

    print("Gateway created for cluster '%s' " % (clusterId), end="", flush=True)

    # Fetch auth_token and gateway port ...
    #
    cmd = 'c=sc._gateway.client.gateway_client; print(c.gateway_parameters.auth_token + "|" + str(c.port))'
    result = command.execute(cmd)
    
    if result[0] != 0:
        print(result[1])
        return None
    
    auth_token, port = result[1].split("|")
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
                  <dt>Master</dt><dd><code>{sc.master}</code></dd>
                </dl>
            </div>
            """.format(sc=spark.sparkContext, uiWebUrl=uiWebUrl)

        return sc_repr_html

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
    def shutdown_kernel(command):
        def handler():
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
            command.close()

        return handler


    atexit.register(shutdown_kernel(command))

    # Forward spark variables to the user namespace
    #
    ip.user_ns["spark"] = spark
    ip.user_ns["sc"] = sc
    ip.user_ns["sqlContext"] = sqlContext
    ip.user_ns["dbutils"] = dbutils
    ip.user_ns["dbbrowser"] = DatabricksBrowser(spark, dbutils)

    print("The following global variables have been created:")
    print("- spark       Spark session")
    print("- sc          Spark context")
    print("- sqlContext  Hive Context")
    print("- dbutils     Databricks utilities (filesystem access only)")
    print("- dbbrowser   Allows to browse dbfs and databases:")
    print("              - dbbrowser.dbfs()")
    print("              - dbbrowser.databases()\n")

    show_status(spark, sparkUi)
    return None


@line_cell_magic
def sql(line, cell=None):
    """Cell magic th execute SQL commands
    
    Args:
        line (str): line behind %sql
        cell (str, optional): cell below %sql. Defaults to None.
    
    Returns:
        DataFrame: DataFrame of the SQL result
    """
    ip = get_ipython()
    spark = ip.user_ns["spark"]
    if cell == None:
        code = line
    else:
        code = cell
    return spark.sql(code)
