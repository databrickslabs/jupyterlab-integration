import json
import queue
import logging
import subprocess
import time

import pytest

from jupyter_client.manager import start_new_kernel

from helpers import get_kernel_path, get_running_clusters, SSH, TEMP


def pytest_generate_tests(metafunc):
    scenarios = []
    for name, cluster_id in get_running_clusters().items():
        for spark in [True, False]:
            scenarios.append((name, {"name": name, "cluster_id": cluster_id, "spark": spark}))
    idlist = []
    argvalues = []
    for scenario in scenarios:
        idlist.append(scenario[0])
        items = scenario[1].items()
        argnames = [x[0] for x in items]
        argvalues.append([x[1] for x in items])
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope="class")


class TestRunKernel:
    CLIENTS = {}

    @staticmethod
    def get_kernel_client(cluster_id, spark, log):
        kernel_name, _ = get_kernel_path(cluster_id, spark)
        if TestRunKernel.CLIENTS.get(kernel_name) is None:
            km, kc = start_new_kernel(
                kernel_name=kernel_name,
                stderr=open("{}{}_std_err.log".format(TEMP, kernel_name), "w"),
                stdout=open("{}{}_std_out.log".format(TEMP, kernel_name), "w"),
            )
            TestRunKernel.CLIENTS[kernel_name] = (km, kc)
        return TestRunKernel.CLIENTS[kernel_name]

    @staticmethod
    def stop_kernel_client(cluster_id, spark, log):
        kernel_name, _ = get_kernel_path(cluster_id, spark)
        km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, log)
        kc.stop_channels()
        km.shutdown_kernel(now=True)
        kc = None
        km = None
        del TestRunKernel.CLIENTS[kernel_name]

    def setup_method(self):
        self.log = logging.getLogger("TestRunKernel")

    def test_ipykernel_before_start(self, name, cluster_id, spark):
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_output([SSH, cluster_id, "pgrep -fal ipykernel"])

    def test_start_kernel(self, name, cluster_id, spark):
        self.log.info("Paramters: %s %s %s", name, cluster_id, spark)
        kernel_name, _ = get_kernel_path(cluster_id, spark)

        km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, self.log)
        self.log.info("Kernel: %s %s", km, kc)
        ready = False
        while not ready:
            try:
                kc_msg = kc.get_iopub_msg(timeout=2, block=True)
                self.log.info(
                    "trace_back: %s, execution_state: %s",
                    kc_msg["content"].get("trace_back"),
                    kc_msg["content"].get("execution_state"),
                )
                assert kc_msg["content"].get("traceback") is None
                ready = kc_msg["content"].get("execution_state") == "idle"
            except queue.Empty:
                ready = True

        with open("{}{}_std_err.log".format(TEMP, kernel_name), "r") as fd:
            stderr = fd.read()
        self.log.info("stderr:\n%s", stderr)
        with open("{}{}_std_out.log".format(TEMP, kernel_name), "r") as fd:
            stdout = fd.read()
        self.log.info("stdout:\n%s", stdout)

    def kernel_execute(self, kc, cmd, user_expressions, expected):
        result = kc.execute_interactive(
            cmd, silent=True, store_history=False, user_expressions=user_expressions
        )
        self.log.info("spark: %s", result["content"])
        assert result["content"]["status"] != "error"
        assert result["content"]["user_expressions"]["result"]["status"] == "ok"
        assert result["content"]["user_expressions"]["result"]["data"]["text/plain"] == expected

    def test_hostname(self, name, cluster_id, spark):
        km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, self.log)
        l = len(cluster_id)
        self.kernel_execute(
            kc,
            cmd="import socket; result = socket.gethostname()",
            user_expressions={"result": "result[:%d]" % l},
            expected="'%s'" % cluster_id,
        )

    def test_simple_command(self, name, cluster_id, spark):
        km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, self.log)
        self.kernel_execute(kc, cmd="a = 42", user_expressions={"result": "a"}, expected="42")

    def test_spark_version(self, name, cluster_id, spark):
        if spark:
            time.sleep(2)
            km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, self.log)
            self.kernel_execute(
                kc,
                cmd="result = spark.version",
                user_expressions={"result": "result[:2]"},
                expected="'3.'" if "7" in name else "'2.'",
            )

    def test_dbfs(self, name, cluster_id, spark):
        if spark:
            km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, self.log)
            self.kernel_execute(
                kc,
                cmd='result = "FileStore/" in [f.name for f in dbutils.fs.ls("/")]',
                user_expressions={"result": "result"},
                expected="True",
            )

    def test_secrets(self, name, cluster_id, spark):
        if spark:
            km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, self.log)
            self.kernel_execute(
                kc,
                cmd='result = dbutils.secrets.get("dbjl-pytest", "pytest-key")',
                user_expressions={"result": "result"},
                expected="'databrickslabs-jupyterlab'",
            )

    def test_rdd(self, name, cluster_id, spark):
        if spark:
            km, kc = TestRunKernel.get_kernel_client(cluster_id, spark, self.log)
            self.kernel_execute(
                kc,
                cmd="result = sc.range(0,10).map(lambda x:x*x).collect()",
                user_expressions={"result": "result"},
                expected="[0, 1, 4, 9, 16, 25, 36, 49, 64, 81]",
            )

    def test_ipykernel(self, name, cluster_id, spark):
        result = subprocess.check_output([SSH, cluster_id, "pgrep -fal ipykernel"])
        self.log.info("ipykernel: %s", result)

    def test_stop_kernel(self, name, cluster_id, spark):
        TestRunKernel.stop_kernel_client(cluster_id, spark, self.log)

    def test_ipykernel_after_shutdown(self, name, cluster_id, spark):
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_output([SSH, cluster_id, "pgrep -fal ipykernel"])
