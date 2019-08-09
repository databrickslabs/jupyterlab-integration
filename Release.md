# Release documentation

## Release check list

- **If backend changed, change version of python package**

    Increase the version in `databricks_jupyterlab._version` This will automatically be used in `setup.py`

- **If labextension changed, change version of typescript labextension**

    Increase the version in `extensions/databricks_jupyterlab_status/package.json`

- **New DBR plugin(s)**

    For every new supported DBR version add a plugin to `dbr-env-file-plugins` and run `make envs`

- **Wheel for remote installation**

    Every install step will deploy databricks-jupyterlab via ssh onto the driver. Before publishing the latest wheel needs to added to the package and run `make wheel`

## Release

- **Python package**

    For the time being this is a pure github provided tool and available from `pypi.org`.

- **Labextension**

    For the time being this is a pure github provided tool and available from `npmjs.com`. 

To release create a tag for the repository and push the tag.
