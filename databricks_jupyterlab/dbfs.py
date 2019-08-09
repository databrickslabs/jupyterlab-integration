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
import re

from sidecar import Sidecar
from ipywidgets import Select, VBox, HBox, Button, Output
from IPython.display import display


class Dbfs(object):

    instance = None

    class __Dbfs(object):
        def __init__(self, dbutils):
            self.dbutils = dbutils

        def create(self):
            self.sc = Sidecar(title="DBFS-%s" % os.environ["DBJL_CLUSTER"].split("-")[-1])
            self.path = "/"
            self.flist = Select(options=[], rows=40, disabled=False)
            self.flist.observe(self.on_click, names='value')

            self.refresh = Button(description="refresh")
            self.refresh.on_click(self.on_refresh)
            self.output = Output()

            self.up = Button(description="up")
            self.up.on_click(self.on_up)

            with self.sc:
                display(VBox([HBox([self.up, self.refresh]), self.flist, self.output]))

            self.update()

        def convertBytes(self, fsize):
            size = fsize
            unit = "B"
            if size > 1024 * 1024 * 1024 * 10:
                size = int(size / 1024.0 / 1024.0 / 1024.0)
                unit = "GB"
            elif size > 1024 * 1024 * 10:
                size = int(size / 1024.0 / 1024.0)
                unit = "MB"
            elif size > 1024 * 10:
                size = int(size / 1024.0)
                unit = "KB"
            return (size, unit)

        def update(self):
            with self.output:
                print("updating ...")
            fobjs = self.dbutils.fs.ls(self.path)
            self.show_path(self.path)

            dirs = sorted([fobj.name for fobj in fobjs if fobj.isDir()], key=lambda x: x.lower())
            files = sorted(
                ["%s (%d %s)" % ((fobj.name, ) + self.convertBytes(fobj.size)) for fobj in fobjs if not fobj.isDir()],
                key=lambda x: x[0].lower())
            self.flist.options = [""] + dirs + files

        def show_path(self, path):
            self.output.clear_output()
            with self.output:
                print("dbfs:" + re.sub(r"\s\(.*?\)$", "", path))

        def on_refresh(self, b):
            self.update()

        def on_up(self, b):
            new_path = os.path.dirname(self.path.rstrip("/"))
            if new_path != self.path:
                self.path = new_path
            self.update()

        def on_click(self, change):
            new_path = os.path.join(self.path, change["new"])
            if change["old"] is not None:
                if change["new"][-1] == "/":
                    self.path = new_path
                    self.update()
                else:
                    self.show_path(new_path)

        def close(self):
            self.sc.close()

    def __init__(self, dbutils=None):
        if not Dbfs.instance:
            Dbfs.instance = Dbfs.__Dbfs(dbutils)

    def __getattr__(self, name):
        return getattr(self.instance, name)