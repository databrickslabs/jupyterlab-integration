#!/bin/bash

mkdir -p databricks_jupyterlab/lib
rm -f databricks_jupyterlab/lib/*
rm -f dist/*.whl
python3 setup.py bdist_wheel
cp dist/databricks_jupyterlab-*-py3-none-any.whl databricks_jupyterlab/lib/
rm -fr dist
rm -fr build
rm -fr databricks_jupyterlab.egg-info

echo -e "\nCreated databricks_jupyterlab/lib/$(ls databricks_jupyterlab/lib/)\n"
