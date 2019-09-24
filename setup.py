import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "databrickslabs_jupyterlab",
    version = "1.0.2-rc8",
    author = "Bernhard Walter",
    author_email = "bernhard.walter@databricks.com",
    url="https://github.com/databrickslabs/Jupyterlab-Integration",
    description = ("Remote Jupyter Lab kernel for Databricks"),
    long_description_content_type='text/markdown',
    license = "Databricks License",
    keywords = "databricks jupyter jupyterlab spark",
    packages=find_packages(),
    scripts=['databrickslabs-jupyterlab'],
    install_requires=[
        'notebook==6.0.1',
        'inquirer',
        'ssh_config',
        'databricks_cli'
    ],
    data_files=[
        ('etc/jupyter/jupyter_notebook_config.d', ['databrickslabs_jupyterlab/status/etc/serverextension.json']),
    ],
    include_package_data=True,
    long_description=read('PYPI.md'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: Other/Proprietary License",
    ],
    zip_safe=False
)
