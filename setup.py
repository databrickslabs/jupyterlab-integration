from glob import glob
import os
from setuptools import setup, find_packages

here = os.path.dirname(os.path.abspath(__file__))

version_ns = {}
with open(os.path.join(here, 'databrickslabs_jupyterlab', '_version.py')) as f:
    exec(f.read(), {}, version_ns)

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "databrickslabs_jupyterlab",
    version = version_ns['__version__'],
    author = "Bernhard Walter",
    author_email = "bernhard.walter@databricks.com",
    description = ("Remote Jupyter Lab kernel for Databricks"),
    license = "Databricks License",
    keywords = "databricks jupyter jupyterlab spark",
    packages=find_packages(),
    scripts=[
        'databrickslabs-jupyterlab', 
        'databrickslabs-vscode'
    ],
    install_requires=['notebook'],
    data_files=[
        ('etc/jupyter/jupyter_notebook_config.d', ['databrickslabs_jupyterlab/status/etc/serverextension.json']),
    ],
    include_package_data=True,
    long_description=read('Readme.md'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: Other/Proprietary License :: Databricks License",
    ],
    zip_safe=False
)
