#   Copyright 2019 Bernhard Walter
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os

def browse_dbfs(dbutils):
    from .dbfs import Dbfs
    Dbfs(dbutils).create()


def browse_databases(spark):
    from .database import Databases
    Databases(spark).create()

if os.environ.get("DBJL_HOST") is None:

    from databricks_jupyterlab.status import KernelHandler, DbStartHandler, DbStatusHandler
    from notebook.utils import url_path_join

    def load_jupyter_server_extension(nbapp):
        """
        Called during notebook start
        """
        print("Loading server extension ...")
        KernelHandler.NBAPP = nbapp
        base_url = nbapp.web_app.settings['base_url']
        status_route = url_path_join(base_url, '/db-status')
        start_route = url_path_join(base_url, '/db-start')
        nbapp.web_app.add_handlers('.*', [(status_route, DbStatusHandler), (start_route, DbStartHandler)])
