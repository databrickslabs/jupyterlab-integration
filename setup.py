import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "databricks_jupyterlab",
    version = "0.1.0",
    author = "Bernhard Walter",
    author_email = "bernhard.walter@databricks.com",
    description = ("Remote Jupyter Lab kernel for Databricks"),
    license = "Apache 2.0",
    keywords = "databricks jupyter jupyterlab spark",
    packages=['databricks_jupyterlab'],
    scripts=['databricks-jupyterlab', 'databricks-vscode'],
    include_package_data=True,
    long_description=read('Readme.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache 2.0 License",
    ]
)