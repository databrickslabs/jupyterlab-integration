import os
from databrickslabs_jupyterlab._version import __version__, __version_info__

if os.environ.get("DBJL_HOST") is None:

    from databrickslabs_jupyterlab.status import KernelHandler, DbStartHandler, DbStatusHandler
    from notebook.utils import url_path_join

    def load_jupyter_server_extension(nbapp):
        """
        Called during notebook start
        """
        print("Loading server extension ...")
        KernelHandler.nbapp = nbapp
        base_url = nbapp.web_app.settings['base_url']
        status_route = url_path_join(base_url, '/databrickslabs-jupyterlab-status')
        start_route = url_path_join(base_url, '/databrickslabs-jupyterlab-start')
        nbapp.web_app.add_handlers('.*', [(status_route, DbStatusHandler), (start_route, DbStartHandler)])
