import os
import platform
import re
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def notebook_version():
    with open("env.yml", "r") as fd:
        env = fd.read()
    r = re.compile("notebook==.*\n")
    nb = r.search(env).group().strip().split("==")[1]
    return nb


EXTRAS_REQUIRE = {}

INSTALL_REQUIRES = []

# Do not install on the Databricks cluster
if os.environ.get("DB_HOME") is None:
    INSTALL_REQUIRES = [
        "notebook==%s" % notebook_version(),
        "version_parser",
        "questionary",
        "databricks_cli",
    ]
    EXTRAS_REQUIRE = {"dev": ["pytest", "jupyter-console", "pyyaml"]}

setup(
    name="databrickslabs_jupyterlab",
    version="2.1.0-rc3",
    author="Bernhard Walter",
    author_email="bernhard.walter@databricks.com",
    url="https://github.com/databrickslabs/Jupyterlab-Integration",
    description=("Remote JupyterLab kernel for Databricks"),
    long_description_content_type="text/markdown",
    license="Databricks License",
    keywords="databricks jupyter jupyterlab spark",
    packages=find_packages(),
    scripts=["databrickslabs-jupyterlab", "dj", "dj.bat"],
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    data_files=[
        (
            "etc/jupyter/jupyter_notebook_config.d",
            ["databrickslabs_jupyterlab/status/etc/serverextension.json"],
        ),
    ],
    include_package_data=True,
    long_description=read("PYPI.md"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: Other/Proprietary License",
    ],
    zip_safe=False,
)
