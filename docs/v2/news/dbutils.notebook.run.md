## Use Databricks dbutils.notbook.run in JupyterLab Integration

Higher compatibility with Databricks notebooks.

- `dbutils.notebook.exit` stops "Running all cells" *[(DEMO)](docs/v2/news/dbutils.notebook.exit.md)* 
- `dbutils.notebook.run` allows to run `.py`and `.ipynb` files from notebooks in JupyterLab Integration 

Note:

- With `dbutils.noteboook.run` the prefix `dbfs:/`and the extension `.ipynb`or `.py`can be omitted
- With `%run` the full **POSIX* path is necessary (including extension): `/dbfs/path/to/notebook.ipynb`
- This feature does not use the implementation of Databricks, but is a complete re-implementation for JupyterLab

![dbutils.notebook.run](dbutils.notebook.run.gif)