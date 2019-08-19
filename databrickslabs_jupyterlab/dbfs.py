import os
import re

from sidecar import Sidecar
from ipywidgets import Select, VBox, HBox, Button, Output
from IPython.display import display


class Dbfs(object):
    """Singleton for the DBFS object"""

    instance = None

    class __Dbfs(object):
        """Database browser implementation
            
        Args:
            dbutils (DBUtils): DBUtils object (for fs only)
        """
        def __init__(self, dbutils):
            self.dbutils = dbutils

        def create(self):
            """Create the sidecar view"""
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
            """Convert bytes to largest unit
            
            Args:
                fsize (int): Size in bytes
            
            Returns:
                tuple: size of largest unit, largest unit
            """
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
            """Update the view when an element was selected"""
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
            """Show path in output widget
            
            Args:
                path (str): Currently selected path
            """
            self.output.clear_output()
            with self.output:
                print("dbfs:" + re.sub(r"\s\(.*?\)$", "", path))

        def on_refresh(self, b):
            """Refresh handler
            
            Args:
                b (ipywidgets.Button): clicked button
            """
            self.update()

        def on_up(self, b):
            """Up handler
            
            Args:
                b (ipywidgets.Button): clicked button
            """
            new_path = os.path.dirname(self.path.rstrip("/"))
            if new_path != self.path:
                self.path = new_path
            self.update()

        def on_click(self, change):
            """Click handler providing db and parent as context
            
            Args:
                db (str): database name
                parent (object): parent object
            """
            new_path = os.path.join(self.path, change["new"])
            if change["old"] is not None:
                if change["new"][-1] == "/":
                    self.path = new_path
                    self.update()
                else:
                    self.show_path(new_path)

        def close(self):
            """Close view"""
            self.sc.close()

    def __init__(self, dbutils=None):
        """Singleton initializer
        
        Args:
            dbutils (DBUtils, optional): DBUtils object. Defaults to None.
        """
        if not Dbfs.instance:
            Dbfs.instance = Dbfs.__Dbfs(dbutils)

    def __getattr__(self, name):
        """Singleton getattr overload"""
        return getattr(self.instance, name)