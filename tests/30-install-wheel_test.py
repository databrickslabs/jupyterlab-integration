import json
import subprocess
import os

from helpers import get_running_clusters
import pytest


def pytest_generate_tests(metafunc):
    scenarios = [
        (name, {"name": name, "cluster_id": cluster_id})
        for name, cluster_id in get_running_clusters().items()
    ]
    idlist = []
    argvalues = []
    for scenario in scenarios:
        idlist.append(scenario[0])
        items = scenario[1].items()
        argnames = [x[0] for x in items]
        argvalues.append([x[1] for x in items])
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope="class")


class TestRunKernel:
    @pytest.mark.skip(reason="Do not install local wheel")
    def test_install_wheel(self, name, cluster_id):
        os.environ["CLUSTER"] = cluster_id
        subprocess.check_output(["make", "install_wheel"], cwd=os.path.dirname(os.getcwd()))
        del os.environ["CLUSTER"]
