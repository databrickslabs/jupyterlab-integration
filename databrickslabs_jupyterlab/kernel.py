from databrickslabs_jupyterlab.local import get_db_config
from databrickslabs_jupyterlab.rest import Command, DatabricksApiException
from ssh_ipykernel.status import Status
from ssh_ipykernel.kernel import SshKernel


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

    def set_spark_running(self):
        """Set current status to Status.SPARK_RUNNING
        """
        self._set_status(DatabricksKernelStatus.SPARK_RUNNING, self.get_pid(), self.is_sudo())


class DatabricksKernel(SshKernel):
    def __init__(self, host, connection_info, python_path, sudo, timeout, env):
        super().__init__(host, connection_info, python_path, sudo, timeout, env)
        self.dbjl_env = dict([e.split("=") for e in env[0].split(" ")])
        self._logger.debug("Environment = {}".format(self.env))
        self._logger.debug("==> kernel: " + str(connection_info))
        self.kernel_status = DatabricksKernelStatus(connection_info, self._logger)
        self.command = None

    def kernel_customize(self):
        self._logger.debug("Create Spark Session")

        profile = self.dbjl_env.get("DBJL_PROFILE", None)
        if profile is None:
            self._logger.error("Environment variable DBJL_PROFILE is not set")
            return None

        cluster_id = self.dbjl_env.get("DBJL_CLUSTER", None)
        if cluster_id is None:
            self._logger.error("Environment variable DBJL_CLUSTER is not set")
            return None

        host, token = get_db_config(profile)

        self._logger.debug("profile={}, host={}, cluster_id={}".format(profile, host, cluster_id))

        try:
            self.command = Command(url=host, cluster_id=cluster_id, token=token)
        except DatabricksApiException as ex:
            self._logger.error(str(ex))
            return None

        self._logger.info("Gateway created for cluster '{}'".format(cluster_id))

        # Fetch auth_token and gateway port ...
        #
        try:
            cmd = 'c=sc._gateway.client.gateway_client; print(c.gateway_parameters.auth_token + "|" + str(c.port))'
            result = self.command.execute(cmd)
        except Exception as ex:
            result = (-1, str(ex))

        if result[0] != 0:
            self._logger.error("error {}: {}".format(*result))
            return None

        gw_token, gw_port = result[1].split("|")
        gw_port = int(gw_port)
        self._logger.debug("Gateway token={}, port={}".format(gw_token, gw_port))

        cmd = (
            "from databrickslabs_jupyterlab.connect import dbcontext, is_remote; "
            + "dbcontext(progressbar=True, gw_port={gw_port}, gw_token='{gw_token}')".format(
                gw_port=gw_port, gw_token=gw_token
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
                self.kernel_status.set_unreachable(self.kernel_pid, True)  # CORRECT IT !!!!!!!!!

        except Exception as ex:
            self._logger.error("Error: " + str(ex))
            self.kernel_status.set_connect_failed()

    def close(self):
        self.command.close()
        super().close()
