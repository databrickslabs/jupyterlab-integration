#!/bin/bash

mkdir -p databrickslabs_jupyterlab/lib
rm -f databrickslabs_jupyterlab/lib/*
rm -f dist/*.whl
python3 setup.py bdist_wheel
cp dist/databrickslabs_jupyterlab-*-py3-none-any.whl databrickslabs_jupyterlab/lib/
rm -fr dist
rm -fr build
rm -fr databrickslabs_jupyterlab.egg-info

echo -e "\nCreated databrickslabs_jupyterlab/lib/$(ls databrickslabs_jupyterlab/lib/)\n"
