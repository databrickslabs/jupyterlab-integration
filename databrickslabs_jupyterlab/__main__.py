import argparse
import json
import os
import sys
from ssh_ipykernel.kernel import SshKernel
from databrickslabs_jupyterlab.local import get_db_config
from databrickslabs_jupyterlab.rest import Command, DatabricksApiException
from databrickslabs_jupyterlab.connect import dbcontext


class DatabricksKernel(SshKernel):
    def __init__(self, host, connection_info, python_path, sudo, timeout, env):
        super().__init__(host, connection_info, python_path, sudo, timeout, env)
        self.dbjl_env = dict([e.split("=") for e in env[0].split(" ")])
        self._logger.debug("Environment = {}".format(self.env))
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
            self._logger.debug("result={}".format(result))
        except Exception as ex:
            result = (-1, str(ex))

        self._logger.debug("result={}".format(result))

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
        result = self.kc.execute_interactive(
            cmd, silent=True, store_history=False, user_expressions={"spark": "spark.version"}
        )
        self._logger.info(result)

    def close(self):
        self.command.close()
        super().close()


def main(host, connection_info, python_path, sudo, timeout, env):
    """Main function to be called as module to create DatabricksKernel

    Arguments:
        host {str} -- host where the remote ipykernel should be started
        connection_info {dict} -- Local ipykernel connection info as provided by Juypter lab
        python_path {str} -- Remote python path to be used to start ipykernel
        sudo {bool} -- Start ipykernel as root if necessary (default: {False})
        timeout {int} -- SSH connection timeout (default: {5})
        env {str} -- Environment variables passd to the ipykernel "VAR1=VAL1 VAR2=VAL2" (default: {""})
    """
    kernel = DatabricksKernel(host, connection_info, python_path, sudo, timeout, env)
    try:
        kernel.create_remote_connection_info()
        kernel.start_kernel_and_tunnels()
    except:
        kernel._logger.error("Kernel could not be started")
    kernel._logger.info("Kernel stopped")
    kernel.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    #    parser._action_groups.pop()
    optional = parser.add_argument_group("optional arguments")
    optional.add_argument(
        "--help",
        "-h",
        action="help",
        default=argparse.SUPPRESS,
        help="show this help message and exit",
    )
    optional.add_argument(
        "--timeout", "-t", type=int, help="timeout for remote commands", default=5
    )
    optional.add_argument(
        "--env",
        "-e",
        nargs="*",
        help="environment variables for the remote kernel in the form: VAR1=value1 VAR2=value2",
    )
    optional.add_argument(
        "-s", action="store_true", help="sudo required to start kernel on the remote machine"
    )

    required = parser.add_argument_group("required arguments")
    required.add_argument("--file", "-f", required=True, help="jupyter kernel connection file")
    required.add_argument("--host", "-H", required=True, help="remote host")
    required.add_argument("--python", "-p", required=True, help="remote python_path")
    args = parser.parse_args()

    try:
        with open(args.file, "r") as fd:
            connection_info = json.loads(fd.read())
    except Exception as ex:
        print(ex)
        sys.exit(1)

    sys.exit(main(args.host, connection_info, args.python, args.s, args.timeout, args.env))
