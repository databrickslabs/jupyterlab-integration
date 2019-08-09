from glob import glob
import os
from setuptools import setup, find_packages

here = os.path.dirname(os.path.abspath(__file__))

version_ns = {}
with open(os.path.join(here, 'databricks_jupyterlab', '_version.py')) as f:
    exec(f.read(), {}, version_ns)

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "databricks_jupyterlab",
    version = version_ns['__version__'],
    author = "Bernhard Walter",
    author_email = "bernhard.walter@databricks.com",
    description = ("Remote Jupyter Lab kernel for Databricks"),
    license = "Apache 2.0",
    keywords = "databricks jupyter jupyterlab spark",
    packages=find_packages(),
    scripts=[
        'databricks-jupyterlab', 
        'databricks-vscode'
    ],
    install_requires=['notebook'],
    data_files=[
        ('etc/jupyter/jupyter_notebook_config.d', ['databricks_jupyterlab/status/etc/serverextension.json']),
    ],
    include_package_data=True,
    long_description=read('Readme.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache 2.0 License",
    ],
    zip_safe=False
)
