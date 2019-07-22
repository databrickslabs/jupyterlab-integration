#!/bin/bash

PROFILE=$1

if [[ -z "$1" ]]; then
    echo "Usage $(basename $0) <profile>"
    exit 1
fi
ssh $PROFILE -p 2200 -t sudo /databricks/python3/bin/python3
