import json
import os
import logging
import subprocess

import yaml

from ssh_config import SSHConfig

from databrickslabs_jupyterlab.remote import (
    #    configure_ssh,
    #    download_notebook,
    get_cluster,
    get_python_path,
    install_libs,
    is_reachable,
    #    version_check,
)

from databrickslabs_jupyterlab.local import (
    #    conda_version,
    create_kernelspec,
    get_db_config,
    prepare_ssh_config,
    #    remove_kernelspecs,
    #    show_profiles,
    #    write_config,
)

from helpers import get_kernel_path, get_running_clusters, get_profile, get_orgid, is_azure, is_aws

EXE = "../databrickslabs-jupyterlab"


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


class TestKernelSpec:
    def setup_method(self):
        self.profile = get_profile()
        self.host, self.token = get_db_config(self.profile)
        self.org = get_orgid()
        self.log = logging.getLogger("TestKernelSpec")

    def test_configure_ssh(self, name, cluster_id):
        cluster_id2, public_ip, cluster_name, _ = get_cluster(self.profile, cluster_id)
        assert cluster_id2 == cluster_id
        assert cluster_name == name
        assert public_ip is not None

        prepare_ssh_config(cluster_id, self.profile, public_ip)
        ssh_config = os.path.expanduser("~/.ssh/config")
        sc = SSHConfig.load(ssh_config)
        host = sc.get(cluster_id)
        assert host.get("ConnectTimeout") == "5"
        assert host.get("ServerAliveCountMax") == "5760"
        assert host.get("IdentityFile") == "~/.ssh/id_{}".format(self.profile)

        assert is_reachable(public_dns=public_ip)

    def test_ssh(self, name, cluster_id):
        subprocess.check_output(["ssh", cluster_id, "hostname"])

    def test_install_libs(self, name, cluster_id):
        result = install_libs(cluster_id, self.host, self.token)
        self.log.info("result: %s", result)

    def test_kernelspec_spark(self, name, cluster_id):
        python_path = get_python_path(cluster_id)

        create_kernelspec(
            self.profile,
            self.org,
            self.host,
            cluster_id,
            name,
            os.environ["CONDA_DEFAULT_ENV"],
            python_path,
            False,
        )

        kernel_path = get_kernel_path(cluster_id, True)[1]
        with open(kernel_path + "/kernel.json") as fd:
            k = json.load(fd)
            assert k["display_name"] == "SSH {} {}:{} ({}/Spark)".format(
                cluster_id, self.profile, name, os.environ["CONDA_DEFAULT_ENV"]
            )

    def test_kernelspec_no_spark(self, name, cluster_id):
        python_path = get_python_path(cluster_id)

        create_kernelspec(
            self.profile,
            self.org,
            self.host,
            cluster_id,
            name,
            os.environ["CONDA_DEFAULT_ENV"],
            python_path,
            True,
        )

        kernel_path = get_kernel_path(cluster_id, False)[1]
        with open(kernel_path + "/kernel.json") as fd:
            k = json.load(fd)
            assert k["display_name"] == "SSH {} {}:{} ({})".format(
                cluster_id, self.profile, name, os.environ["CONDA_DEFAULT_ENV"]
            )

    def test_create(self, name, cluster_id):
        result = None
        if is_aws():
            result = subprocess.check_output([EXE, self.profile, "-k", "-i", cluster_id])
        if is_azure():
            if self.host.startswith("https://"):
                result = subprocess.check_output([EXE, self.profile, "-k", "-i", cluster_id])
            else:
                result = subprocess.check_output(
                    [EXE, self.profile, "-k", "-o", str(self.org), "-i", cluster_id]
                )

        assert result is not None
        self.log.info("result %s", result)

    def test_reconfigure(self, name, cluster_id):
        result = None
        if is_aws():
            result = subprocess.check_output([EXE, self.profile, "-r", "-i", cluster_id])
        if is_azure():
            if self.host.startswith("https://"):
                result = subprocess.check_output([EXE, self.profile, "-r", "-i", cluster_id])
            else:
                result = subprocess.check_output(
                    [EXE, self.profile, "-r", "-o", str(self.org), "-i", cluster_id]
                )
        assert result is not None
        self.log.info("result %s", result)

    def test_ssh_2(self, name, cluster_id):
        subprocess.check_output(["ssh", cluster_id, "hostname"])
