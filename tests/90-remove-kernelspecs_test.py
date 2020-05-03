import json
import os

from jupyter_client import kernelspec
from ssh_config import SSHConfig
import pytest

from helpers import get_test_kernels


class TestRemoveConfig:
    def setup_method(self):
        with open("/tmp/running_clusters.json", "r") as fd:
            self.clusters = json.load(fd)

    # @pytest.mark.skip(reason="Keep kernelspecs")
    def test_remove_kernelspecs(self):
        km = kernelspec.KernelSpecManager()
        for kernel_name in get_test_kernels():
            km.remove_kernel_spec(kernel_name)

    # @pytest.mark.skip(reason="Keep known_hosts entries")
    def test_remove_known_host_entries(self):
        known_hosts_file = os.path.expanduser("~/.ssh/known_hosts")
        with open(known_hosts_file, "r") as fd:
            known_hosts = fd.read()

        config = os.path.expanduser("~/.ssh/config")
        try:
            sc = SSHConfig.load(config)
        except:  # pylint: disable=bare-except
            sc = SSHConfig(config)

        test_addresses = [
            h.get("HostName") for h in sc.hosts() if h.name in list(self.clusters.values())
        ]
        test_ips = [".".join(a.split(".")[0].split("-")[1:]) for a in test_addresses]
        keep_addresses = []
        for line in known_hosts.split("\n"):
            if line.strip() != "":
                address = line.split("]:2200")[0][1:]
                if not address in test_addresses and not address in test_ips:
                    keep_addresses.append(line)
        with open(known_hosts_file, "w") as fd:
            fd.write("\n".join(keep_addresses))

    # @pytest.mark.skip(reason="Keep ssh config")
    def test_remove_ssh_config(self):
        config = os.path.expanduser("~/.ssh/config")
        try:
            sc = SSHConfig.load(config)
        except:  # pylint: disable=bare-except
            sc = SSHConfig(config)
        for host in list(self.clusters.values()):
            sc.remove(host)
        sc.write()
