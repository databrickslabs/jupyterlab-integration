#!/bin/bash

prefix=dbr-env-file-plugins

for plugin in $(ls $prefix/*.yml-plugin); do
    filename=$(basename $plugin)
    cat $prefix/env-master.yml $plugin > "env-${filename%.*}.yml"
done