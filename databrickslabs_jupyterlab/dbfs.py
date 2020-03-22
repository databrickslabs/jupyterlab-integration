import os
import re

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

        def create(self, rows=30, path="/", height="400px"):
            self.path = path
            self.flist = Select(options=[], disabled=False, layout={"height": height})
            self.flist.observe(self.on_click, names="value")

            self.refresh = Button(icon="refresh", layout={"width": "40px"})
            self.refresh.on_click(self.on_refresh)
            self.path_view = Output()
            self.preview = Output(
                layout={
                    "width": "800px",
                    "height": height,
                    "overflow": "scroll",
                    "border": "1px solid gray",
                }
            )

            self.up = Button(icon="arrow-up", layout={"width": "40px"})
            self.up.on_click(self.on_up)

            display(
                VBox(
                    [
                        HBox([self.refresh, self.up, self.path_view]),
                        HBox([self.flist, self.preview]),
                    ]
                )
            )

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
            self.path_view.clear_output()
            self.preview.clear_output()
            with self.path_view:
                print("updating ...")
            try:
                fobjs = self.dbutils.fs.ls(self.path)
            except Exception as ex:
                with self.path_view:
                    print("Error: Cannot access folder")
                return False

            self.show_path(self.path)

            dirs = sorted([fobj.name for fobj in fobjs if fobj.isDir()], key=lambda x: x.lower())
            files = sorted(
                [
                    "%s (%d %s)" % ((fobj.name,) + self.convertBytes(fobj.size))
                    for fobj in fobjs
                    if not fobj.isDir()
                ],
                key=lambda x: x[0].lower(),
            )
            self.flist.options = [""] + dirs + files
            return True

        def show_path(self, path):
            """Show path in output widget
            
            Args:
                path (str): Currently selected path
            """
            self.path_view.clear_output()
            with self.path_view:
                print("dbfs:" + re.sub(r"\s\(.*?\)$", "", path))

        def show_preview(self, path):
            """Show preview of csv, md or txt in output widget
            
            Args:
                path (str): Currently selected path
            """
            real_path = re.sub(r"\s\(.*?\)$", "", path)
            parts = real_path.split(".")
            if len(parts) > 0 and parts[-1].lower() in [
                "md",
                "csv",
                "txt",
                "sh",
                "sql",
                "py",
                "scala",
                "json",
            ]:
                text = self.dbutils.fs.head(real_path)
                self.preview.clear_output()
                with self.preview:
                    print(text)

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
                    old_path = self.path
                    self.path = new_path
                    if not self.update():
                        self.path = old_path
                else:
                    self.show_path(new_path)
                    self.show_preview(new_path)

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
