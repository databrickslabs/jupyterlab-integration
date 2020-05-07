import json
import os
import platform
import yaml
from jupyter_client import kernelspec

if platform.uname().system == "Windows":
    EXE = "..\\dj.bat"
    RUNNING_FILE = "C:\\Windows\\Temp\\{}_running_clusters.json".format(os.environ["CLOUD"])
else:
    EXE = "../databrickslabs-jupyterlab"
    RUNNING_FILE = "/tmp/{}_running_clusters.json".format(os.environ["CLOUD"])
print(EXE)
print(RUNNING_FILE)


def get_kernel_path(cluster_id, with_spark):
    def cond(k):
        s = k.endswith("spark")
        return s if with_spark else not s

    test_kernels = [
        (k, v)
        for k, v in kernelspec.find_kernel_specs().items()
        if (k.startswith("ssh_"))
        and ("TEST" in kernelspec.get_kernel_spec(k).display_name)
        and (cluster_id in k)
        and cond(k)
    ]
    assert len(test_kernels) == 1
    return test_kernels[0]


def get_test_kernels():
    test_kernels = [
        k
        for k, v in kernelspec.find_kernel_specs().items()
        if (k.startswith("ssh_")) and ("TEST" in kernelspec.get_kernel_spec(k).display_name)
    ]
    return test_kernels


def is_aws():
    # shall raise exception if variable CLOUD not set
    return os.environ["CLOUD"] == "aws"


def is_azure():
    # shall raise exception if variable CLOUD not set
    return os.environ["CLOUD"] == "azure"


def get_profile():
    config = yaml.safe_load(open("clusters.yaml", "r"))
    return config[os.environ["CLOUD"]]["profile"]


def get_instances():
    config = yaml.safe_load(open("clusters.yaml", "r"))
    return config[os.environ["CLOUD"]]["instances"]


def get_orgid():
    config = yaml.safe_load(open("clusters.yaml", "r"))
    return config[os.environ["CLOUD"]]["orgid"]


def get_spark_versions():
    config = yaml.safe_load(open("clusters.yaml", "r"))
    return config["spark_versions"]


def get_running_clusters():
    with open(RUNNING_FILE, "r") as fd:
        clusters = json.load(fd)
    return clusters


def save_running_clusters(cluster_ids):
    print("saving to", RUNNING_FILE)
    with open(RUNNING_FILE, "w") as fd:
        fd.write(json.dumps(cluster_ids))


def remove_running_clusters():
    os.unlink(RUNNING_FILE)
