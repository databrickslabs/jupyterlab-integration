import atexit
import datetime
import glob
import io
import os
import random
import sys
import threading
import uuid
import warnings

from IPython import get_ipython
from IPython.display import HTML, display
from IPython.core.magic import Magics, magics_class, line_cell_magic

from databrickslabs_jupyterlab.rest import Command
from databrickslabs_jupyterlab.progress import load_progressbar, debug
from databrickslabs_jupyterlab.dbfs import Dbfs
from databrickslabs_jupyterlab.database import Databases
from databrickslabs_jupyterlab.notebook import Notebook

py4j = glob.glob("/databricks/spark/python/lib/py4j-*-src.zip")[0]
sys.path.insert(0, py4j)
sys.path.insert(0, "/databricks/spark/python")
sys.path.insert(0, "/databricks/jars/spark--driver--spark--resources-resources.jar")

from pyspark.conf import SparkConf  # pylint: disable=import-error,wrong-import-position

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

from dbutils import DBUtils  # pylint: disable=import-error,wrong-import-position


class JobInfo:
    """Job info class for Spark jobs
    Args:
        sc (SparkContext): Spark Context
    """

    def __init__(self, sc):
        self.pool_id = str(random.getrandbits(64))
        self.group_id = "jupyterlab-default-group"
        self.is_running = {}
        self.current_thread = None
        self.sc = sc

    def dump(self, tag):
        if debug():
            print(
                tag,
                "%s (%s)"
                % (
                    datetime.datetime.now().isoformat(),
                    threading.current_thread().__class__.__name__,
                ),
            )
            print("%s: pool_id              %s" % (tag, self.pool_id))
            print("%s: group_id             %s" % (tag, self.group_id))
            print(
                "%s: spark.scheduler.pool %s"
                % (tag, self.sc.getLocalProperty("spark.scheduler.pool"))
            )
            print(
                "%s: spark.jobGroup.id    %s" % (tag, self.sc.getLocalProperty("spark.jobGroup.id"))
            )
            print("%s: running              %s" % (tag, self.is_running.get(self.group_id, None)))

    def attach(self):
        if debug():
            print(
                "\nATTACHING to ",
                self.group_id,
                "in",
                threading.current_thread().__class__.__name__,
            )
        # Catch [SPARK-22340][PYTHON] Add a mode to pin Python thread into JVM's
        # This code explicitely attaches both python threads to the value Spark Context is set to
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.sc.setLocalProperty("spark.scheduler.pool", self.pool_id)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.sc.setJobGroup(self.group_id, "jupyterlab job group", True)

    def stop_all(self):
        if debug():
            print("\nSTOPPING all running threads")
        for k, v in self.is_running.items():
            if v and debug():
                print("- Job to be stopped:", k)
            self.is_running[k] = False

    def new_group_id(self):
        self.group_id = self.pool_id + "_" + uuid.uuid4().hex
        self.attach()


class DbjlUtils:
    def __init__(self, shell, entry_point):
        self._dbutils = DBUtils(shell, entry_point)
        self.fs = self._dbutils.fs
        self.secrets = self._dbutils.secrets
        self.notebook = Notebook()

    def help(self):
        html = """
        This module provides a subset of the DBUtils tools working for Jupyterlab Integration
        <br/><br/>
        <b>fs: DbfsUtils</b> -&gt; Manipulates the Databricks filesystem (DBFS) from the console
        <br/>
        <b>secrets: SecretUtils</b> -&gt; Provides utilities for leveraging secrets within notebooks
        <br/>
        <b>notebook: NotebookUtils</b> -&gt; Utilities for the control flow of a notebook (EXPERIMENTAL)
        """
        display(HTML(html))


@magics_class
class DbjlMagics(Magics):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = os.environ["DBJL_HOST"]
        self.cluster = os.environ["DBJL_CLUSTER"]
        self.scope = None
        self.key = None
        self.command = None

    @line_cell_magic
    def scala(self, line, cell=None):
        "Magic that allows to execute scala in a notebook"
        if cell is None:
            print("Use %%scala as a cell magic")
        else:
            try:
                command = get_ipython().user_ns["__scalaCommand"]
                result = command.execute(cell, full_result=True)
            except Exception as ex:  # pylint: disable=broad-except
                result = (-1, "%s: %s" % (type(ex), ex))

            if result[0] == 0:
                typ = result[1]["results"]["resultType"]
                data = result[1]["results"]["data"]
                if typ == "text":
                    print(data)
                elif typ == "table":
                    import pandas as pd

                    df = pd.DataFrame(data)
                    df.columns = [c["name"] for c in result[1]["results"]["schema"]]
                    display(df)
                    if result[1]["results"]["truncated"]:
                        print("Data truncated, more than 1000 rows")
            else:
                print("Error: " + result[1]["results"]["cause"])

    @line_cell_magic
    def sql(self, line, cell=None):
        """Cell magic th execute SQL commands

        Args:
            line (str): line behind %sql
            cell (str, optional): cell below %sql. Defaults to None.
        
        Returns:
            DataFrame: DataFrame of the SQL result
        """
        ip = get_ipython()
        spark = ip.user_ns["spark"]
        if cell is None:
            code = line
        else:
            code = cell
        if "explain" in code.lower():
            result = spark.sql(code).collect()
            for plan in result:
                print(plan.plan)
        else:
            return spark.sql(code)

    @line_cell_magic
    def fs(self, line, cell=None):
        """Cell magic to browse DBFS

        Args:
            line (str): line behind %fs
            cell (str, optional): cell below %%fs. Defaults to None.
        
        Returns:
            None
        """

        def confirm(prompt):
            answer = ""
            while answer not in ["y", "n"]:
                answer = input(prompt + " (y/n) ").lower()
            return answer == "y"

        ip = get_ipython()
        dbutils = ip.user_ns["dbutils"]

        if cell is None:
            cmd = line.strip().split()
        else:
            cmd = cell.strip().split()

        if cmd[0] == "cp":
            if cmd[1] in ("--recurse", "-r"):
                if confirm("Recursively copy '{}' to '{}'".format(cmd[2], cmd[3])):
                    dbutils.fs.cp(cmd[2], cmd[3], recurse=True)
                    print("done")
            else:
                if confirm("Copy '{}' to '{}'".format(cmd[1], cmd[2])):
                    dbutils.fs.cp(cmd[1], cmd[2], recurse=False)
                    print("done")

        elif cmd[0] == "head":
            if cmd[1] in ("--maxBytes", "-m"):
                print("Showing head of file '{}' with max. {} bytes:\n".format(cmd[3], cmd[2]))
                print(dbutils.fs.head(cmd[3], max_bytes=int(cmd[2])))
            else:
                print("Show head of file '{}':\n".format(cmd[1]))
                print(dbutils.fs.head(cmd[1]))

        elif cmd[0] == "ls":
            print("List directory '{}':\n".format(cmd[1]))
            for f in dbutils.fs.ls(cmd[1]):
                print(f)

        elif cmd[0] == "mkdirs":
            if confirm("Make dirs '{}'".format(cmd[1])):
                dbutils.fs.mkdirs(cmd[1])
                print("done")

        elif cmd[0] == "mv":
            if cmd[1] in ("--recurse", "-r"):
                if confirm("Recursively moving '{}' to '{}'".format(cmd[2], cmd[3])):
                    dbutils.fs.mv(cmd[2], cmd[3], recurse=True)
                    print("done")
            else:
                if confirm("Moving '{}' to '{}'".format(cmd[1], cmd[2])):
                    dbutils.fs.mv(cmd[1], cmd[2], recurse=False)
                    print("done")

        elif cmd[0] == "put":
            if cmd[1] in ("--overwrite", "-o"):
                if confirm("Overwriting file '{}' with '{}'".format(cmd[2], " ".join(cmd[3:]))):
                    dbutils.fs.put(cmd[2], " ".join(cmd[3:]), overwrite=True)
                    print("done")
            else:
                if confirm("Writing '{}' to file '{}'".format(" ".join(cmd[2:]), cmd[1])):
                    dbutils.fs.put(cmd[1], " ".join(cmd[2:]), overwrite=False)
                    print("done")

        elif cmd[0] == "rm":
            if cmd[1] in ("--recurse", "-r"):
                if confirm("Recursively deleting '{}'".format(cmd[2])):
                    dbutils.fs.rm(cmd[2], recurse=True)
                    print("done")
            else:
                if confirm("Deleting '{}'".format(cmd[1])):
                    dbutils.fs.rm(cmd[1], recurse=False)
                    print("done")


class DatabricksBrowser:
    """[summary]
    Args:
        spark (SparkSession): Spark Session object
        dbutils (DBUtils): DbUtils object
    """

    def __init__(self, spark, dbutils):
        self.spark = spark
        self.dbutils = dbutils

    def dbfs(self, path="/", height="400px"):
        """Start dbfs browser"""
        Dbfs(self.dbutils).create(path, height)

    def databases(self):
        """Start Database browser"""
        Databases(self.spark).create()

    def experiments(self, experiment_name):
        """Start the experiment browser for a given experiment name"""
        from databrickslabs_jupyterlab.mlflow import MLflowBrowser

        return MLflowBrowser(experiment_name)


def dbcontext(progressbar=True, gw_port=None, gw_token=None, token=None, scala_context_id=None):
    """Create a databricks context
    The following objects will be created
    - Spark Session
    - Spark Context
    - Spark Hive Context
    - DBUtils (fs module only)
    
    Args:
        progressbar (bool, optional): If True spark progressbars will be shown. Default: True.
    """

    def get_sparkui_url(host, organisation, clusterId):
        if organisation is None:
            sparkUi = "%s#/setting/clusters/%s/sparkUi" % (host, clusterId)
        else:
            sparkUi = "%s/?o=%s#/setting/clusters/%s/sparkUi" % (host, organisation, clusterId)
        return sparkUi

    def show_status(spark):
        output = """
        <div>
            <dl>
            <dt>Spark Version</dt><dd>{sc.version}</dd>
            <dt>Spark Application</dt><dd>{sc.appName}</dd>
            <dt>Spark UI</dt><dd><a href="{sparkUi}">go to ...</a></dd>
            </dl>
        </div>
        """.format(
            sc=spark.sparkContext,
            sparkUi=get_sparkui_url(host, organisation, clusterId),
            # num_executors=len(spark.sparkContext._jsc.sc().statusTracker().getExecutorInfos()),
        )
        display(HTML(output))

    # Get the configuration injected by the client
    #
    profile = os.environ.get("DBJL_PROFILE", None)
    host = os.environ.get("DBJL_HOST", None)
    clusterId = os.environ.get("DBJL_CLUSTER", None)
    organisation = os.environ.get("DBJL_ORG", None)

    print(
        "Remote init: profile={}, organisation={}. cluster_id={}, host={}".format(
            profile, organisation, clusterId, host
        )
    )
    sparkUi = get_sparkui_url(host, organisation, clusterId)

    print("Remote init: Spark UI = {}".format(sparkUi))

    ip = get_ipython()

    if os.environ.get("DEBUG") == "DEBUG":
        print("Remote init: Gateway port = {}, token = {}".format(gw_port, gw_token))

    interpreter = "/databricks/python/bin/python"
    # Ensure that driver and executors use the same python
    #
    os.environ["PYSPARK_PYTHON"] = interpreter
    os.environ["PYSPARK_DRIVER_PYTHON"] = interpreter

    # ... and connect to this gateway
    #
    try:
        # up to DBR version 6.4
        gateway = get_existing_gateway(gw_port, True, gw_token)
    except TypeError:
        # for DBR 6.5 and higher
        gateway = get_existing_gateway(gw_port, True, gw_token, False)

    print("Remote init: Connected")

    # Retrieve spark session, sqlContext and sparkContext
    #

    conf = SparkConf(_jconf=gateway.entry_point.getSparkConf())
    sc = RemoteContext(gateway=gateway, conf=conf)
    if sc.version < "3.0":
        from pyspark.sql import HiveContext  # pylint: disable=import-error,import-outside-toplevel

        sqlContext = HiveContext(sc, gateway.entry_point.getSQLContext())
    else:
        from pyspark.sql import SQLContext  # pylint: disable=import-error,import-outside-toplevel
        from pyspark.sql.session import (  # pylint: disable=import-error,import-outside-toplevel
            SparkSession,
        )

        jsqlContext = gateway.entry_point.getSQLContext()
        sqlContext = SQLContext(sc, SparkSession(sc, jsqlContext.sparkSession()), jsqlContext)

    spark = sqlContext.sparkSession
    sc = spark.sparkContext

    print("Remote init: Spark Session created")

    # Enable pretty printing of dataframes
    #
    spark.conf.set("spark.sql.repl.eagerEval.enabled", "true")

    # Define a separate pool for the fair scheduler
    #
    job_info = JobInfo(sc)

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
            """.format(
                sc=spark.sparkContext, uiWebUrl=uiWebUrl
            )

        return sc_repr_html

    sc_repr_html = repr_html(sparkUi)
    sc._repr_html_ = sc_repr_html  # pylint: disable=protected-access

    # Monkey patch Databricks Cli to allow mlflow tracking with the credentials provided
    # by this routine
    # Only necessary when mlflow is installed
    #

    print("Remote init: Configuring mlflow")
    try:
        from databricks_cli.configure.provider import (  # pylint: disable=import-outside-toplevel
            ProfileConfigProvider,
            DatabricksConfig,
        )

        def get_config(self):  # pylint: disable=unused-argument
            config = DatabricksConfig(host, None, None, token, False)
            if config.is_valid:
                return config
            return None

        ProfileConfigProvider.get_config = get_config
    except Exception:  # pylint: disable=broad-except
        print("Cannot initialize mlflow")

    # Initialize the ipython shell with spark context
    #
    shell = get_ipython()
    shell.sc = sc
    shell.sqlContext = sqlContext
    shell.displayHTML = lambda html: display(HTML(html))
    shell.user_ns["displayHTML"] = lambda html: display(HTML(html))

    # Retrieve the py4j gateway entrypoint
    #
    entry_point = spark.sparkContext._gateway.entry_point  # pylint: disable=protected-access

    # Initialize dbutils
    #
    dbutils = DbjlUtils(shell, entry_point)

    # Setting up Spark progress bar
    #
    if progressbar:
        # print("Set up Spark progress bar")
        load_progressbar(sc, job_info)

    # Register sql magic
    #
    # ip.register_magic_function(sql, magic_kind="line_cell")
    ip.register_magics(DbjlMagics)

    # Setup scala context

    if scala_context_id is not None:
        print("Remote init: Configuring scala Command")
        try:
            scalaCommand = Command(
                url=host,
                cluster_id=clusterId,
                token=token,
                language="scala",
                scala_context_id=scala_context_id,
            )
            ip.user_ns["__scalaCommand"] = scalaCommand
        except:  # pylint: disable=bare-except
            print("Cannot create scala command, so %%scala will not work")
            scalaCommand = None
    else:
        print("Remote Init: %%scala will not work")

    # Forward spark variables to the user namespace
    #
    ip.user_ns["spark"] = spark
    ip.user_ns["sc"] = sc
    ip.user_ns["sqlContext"] = sqlContext
    ip.user_ns["dbutils"] = dbutils
    ip.user_ns["dbbrowser"] = DatabricksBrowser(spark, dbutils)

    print("Remote init: The following global variables have been created:")
    print("- spark       Spark session")
    print("- sc          Spark context")
    print("- sqlContext  Hive Context")
    print("- dbutils     Databricks utilities (filesystem access only)")
    print("- dbbrowser   Allows to browse dbfs and databases:")
    print("              - dbbrowser.dbfs()")
    print("              - dbbrowser.databases()\n")

    show_status(spark)
    return None
