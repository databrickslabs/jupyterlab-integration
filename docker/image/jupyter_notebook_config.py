# Configuration file for jupyter-notebook.

# ------------------------------------------------------------------------------
# NotebookApp(JupyterApp) configuration
# ------------------------------------------------------------------------------

## The IP address the notebook server will listen on.
c.NotebookApp.ip = "*"

## The directory to use for notebooks and kernels.
c.NotebookApp.notebook_dir = "/home/dbuser/notebooks"

## Whether to open in a browser after starting. The specific browser used is
#  platform dependent and determined by the python standard library `webbrowser`
#  module, unless it is overridden using the --browser (NotebookApp.browser)
#  configuration option.
c.NotebookApp.open_browser = False

## The port the notebook server will listen on.
c.NotebookApp.port = 8888
