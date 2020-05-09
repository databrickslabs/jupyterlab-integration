from ssh_ipykernel.status import Status
from ssh_ipykernel.kernel import SshKernel, SshKernelException
from ssh_ipykernel.utils import setup_logging

from databrickslabs_jupyterlab.local import get_db_config
from databrickslabs_jupyterlab.rest import Command, DatabricksApiException


class DatabricksKernelStatus(Status):
    def __init__(self, connection_info, logger, status_folder="~/.ssh_ipykernel"):
        super().__init__(connection_info, logger, status_folder)
        DatabricksKernelStatus.SPARK_RUNNING = 7
        DatabricksKernelStatus.MESSAGES[
            DatabricksKernelStatus.SPARK_RUNNING
        ] = "SparkSession created"

    def is_spark_running(self):
        """Check for Status.SPARK_RUNNING

        Returns:
            bool -- True if current status is Status.SPARK_RUNNING
        """
        return self._get_status() == DatabricksKernelStatus.SPARK_RUNNING

    def set_spark_running(self, pid=None, sudo=None):
        """Set current status to Status.SPARK_RUNNING
        """
        self._set_status(DatabricksKernelStatus.SPARK_RUNNING, pid, sudo)


class DatabricksKernel(SshKernel):
    def __init__(self, host, connection_info, python_path, sudo, timeout, env, no_spark):
        self._logger = setup_logging("DatabricksKernel")

        self.no_spark = no_spark

        self.dbjl_env = dict([e.split("=") for e in env[0].split(" ")])
        self._logger.debug("Environment = %s", self.dbjl_env)
        self.profile = self.dbjl_env.get("DBJL_PROFILE", None)
        self.host, self.token = get_db_config(self.profile)

        self.cluster_id = self.dbjl_env.get("DBJL_CLUSTER", None)

        self.python_command = None
        self.scala_context_id = None
        if not no_spark:
            # create remote executions context and retrieve its python path
            python_path = self.create_execution_context()
        self._logger.info("Remote python path: %s", python_path)

        super().__init__(
            host,
            connection_info,
            python_path,
            sudo=sudo,
            timeout=timeout,
            env=env,
            logger=self._logger,
        )

        self.kernel_status = DatabricksKernelStatus(connection_info, self._logger)

    def create_execution_context(self):
        if self.profile is None:
            self._logger.error("Environment variable DBJL_PROFILE is not set")
            self.no_spark = True
            return None

        if self.cluster_id is None:
            self._logger.error("Environment variable DBJL_CLUSTER is not set")
            self.no_spark = True
            return None

        self._logger.debug("Create Execution Context")

        self._logger.debug(
            "profile=%s, host=%s, cluster_id=%s", self.profile, self.host, self.cluster_id
        )

        # Create remote Python Context
        try:
            self.python_command = Command(
                url=self.host, cluster_id=self.cluster_id, token=self.token
            )
            self._logger.debug("Created remote Python context %s", self.python_command.context.id)
        except DatabricksApiException as ex:
            self._logger.error(str(ex))
            raise SshKernelException("Cannot create python execution context on remote cluster")

        # Create remote Scala Context
        try:
            self.scala_command = Command(
                url=self.host, cluster_id=self.cluster_id, token=self.token, language="scala"
            )
            self.scala_context_id = self.scala_command.context.id
            self._logger.debug("Created remote Scala context %s", self.scala_context_id)
        except DatabricksApiException as ex:
            self._logger.error(str(ex))
            self._logger.error("Cannot create Scala context, %%scala will not be possible")

        self._logger.info("Gateway created for cluster '%s'", self.cluster_id)

        try:
            cmd = "import sys; print(sys.executable.split('/bin/')[0])"
            result = self.python_command.execute(cmd)
        except Exception as ex:  # pylint: disable=broad-except
            self._logger.error("ERROR %s: %s", type(ex), ex)
            raise SshKernelException("Cannot retrieve python executable from remote cluster")

        return result[1]

    def kernel_customize(self):
        if self.no_spark:
            self._logger.info("This kernel will have no Spark Session (--no-spark)")
            return None

        self._logger.debug("Create Spark Session")

        # Fetch auth_token and gateway port ...
        #
        try:
            cmd = (
                "c=sc._gateway.client.gateway_client; "
                + 'print(c.gateway_parameters.auth_token + "|" + str(c.port))'
            )
            result = self.python_command.execute(cmd)
        except Exception as ex:  # pylint: disable=broad-except
            self._logger.error("ERROR %s: %s", type(ex), ex)
            raise SshKernelException("Cannot retrieve py4j gateway from remote cluster")

        gw_token, gw_port = result[1].split("|")
        gw_port = int(gw_port)
        self._logger.debug("Gateway token=%s, port=%s", gw_token, gw_port)

        cmd = (
            "from databrickslabs_jupyterlab.connect import dbcontext; "
            + "dbcontext(progressbar=True"
            + ", gw_port={}, gw_token='{}', token='{}', scala_context_id='{}')".format(
                gw_port, gw_token, self.token, self.scala_context_id
            )
        )
        try:
            result = self.kc.execute_interactive(
                cmd, silent=True, store_history=False, user_expressions={"spark": "spark.version"}
            )
            if result["content"]["status"] != "error":
                self.kernel_status.set_spark_running()
            else:
                self._logger.error("Error: Cluster unreachable")
                self.kernel_status.set_unreachable()
                raise SshKernelException("Cannot create SparkSession on remote cluster")

        except Exception as ex:  # pylint: disable=broad-except
            self._logger.error("ERROR %s: %s", type(ex), ex)
            self.kernel_status.set_connect_failed()
            raise SshKernelException("Cannot access kernel on remote cluster")

    def close(self):
        if not self.no_spark:
            try:
                self.python_command.close()
                self._logger.info("Remote Python context closed")
            except Exception as ex:  # pylint: disable=broad-except
                self._logger.error("%s: Failed closing Remote Python context: %s", type(ex), ex)
            try:
                self.scala_command.close()
                self._logger.info("Remote Scala context closed")
            except Exception as ex:  # pylint: disable=broad-except
                self._logger.error("%s: Failed closing Remote Scala context: %s", type(ex), ex)

        super().close()
