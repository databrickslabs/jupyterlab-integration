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


INSTALL_REQUIRES = [
]

EXTRAS_REQUIRES = {
    "cli": [
        "notebook>=6.3.0,<6.4.0",
        "version_parser>=1.0.0,<1.1.0",
        "questionary",
        "databricks_cli",         
        "jupyterlab>=3.0.0,<3.1.0",
        "ipywidgets>=7.6.3,<7.7.0",
        "ipykernel>=5.5.3,<5.6.0",
        "tornado>=6.1.0,<6.2.0",
        "widgetsnbextension==3.5.1",
        "ssh-ipykernel==1.2.2",
        "inquirer==2.6.3",
        "pyperclip>=1.8.2<1.9.0",
        "databrickslabs_jupyterlab_status==2.2.0"
    ],
    "dev": [
        "pytest", 
        "jupyter-console", 
        "pyyaml", 
        "bumpversion", 
        "twine", 
        "yapf", 
        "pylint"
    ],
}

setup(
    name="databrickslabs_jupyterlab",
    version="2.2.0",
    author="Bernhard Walter",
    author_email="bernhard.walter@databricks.com",
    url="https://github.com/databrickslabs/Jupyterlab-Integration",
    description=("Remote JupyterLab kernel for Databricks"),
    long_description_content_type="text/markdown",
    license="Databricks License",
    keywords="databricks jupyter jupyterlab spark",
    packages=find_packages(exclude=["databrickslabs-jupyterlab-status"]),
    scripts=["databrickslabs-jupyterlab", "dj", "dj.bat"],
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRES,
    data_files=[
        # (
        #     "etc/jupyter/jupyter_notebook_config.d",
        #     ["databrickslabs_jupyterlab/status/jupyter_notebook/databrickslabs_jupyterlab.json"],
        # ),
        (
            "etc/jupyter/jupyter_server_config.d",
            ["databrickslabs_jupyterlab/status/jupyter_server/databrickslabs_jupyterlab.json"],
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
