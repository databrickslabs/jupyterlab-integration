from jupyter_client import kernelspec


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


# import subprocess


# def get_kernel_path_old(cluster_id, with_spark):
#     kernels = subprocess.check_output(["jupyter-kernelspec", "list"])

#     def cond(k):
#         s = k.endswith("spark")
#         return s if with_spark else not s

#     kernel = [k for k in kernels.decode("utf-8").split("\n") if cluster_id in k and cond(k)]
#     assert len(kernel) == 1
#     return kernel[0].split()
