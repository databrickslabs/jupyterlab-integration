import os
from notebook.utils import url_path_join

from databrickslabs_jupyterlab._version import __version__, __version_info__


def is_remote():
    """Check whether the current context is on the remote cluster
    
    Returns:
        bool: True if remote else False
    """
    return os.environ.get("DBJL_HOST", None) is not None


def is_azure():
    """Check whether the current context is on Azure Databricks
    
    Returns:
        bool: True if Azure Databricks else False
    """
    return os.environ.get("DBJL_ORG", None) is not None


def load_jupyter_server_extension(nbapp):
    """
    Called during notebook start
    """
    if not is_remote():
        from databrickslabs_jupyterlab.status import KernelHandler, DbStartHandler, DbStatusHandler

        KernelHandler.nbapp = nbapp
        base_url = nbapp.web_app.settings["base_url"]
        status_route = url_path_join(base_url, "/databrickslabs-jupyterlab-status")
        start_route = url_path_join(base_url, "/databrickslabs-jupyterlab-start")
        nbapp.web_app.add_handlers(
            ".*", [(status_route, DbStatusHandler), (start_route, DbStartHandler)]
        )
