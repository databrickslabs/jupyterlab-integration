import os
import re

import pandas as pd

from ipywidgets import Select, VBox, HBox, Button, Output
from IPython.display import display, HTML, Markdown, Code, Image


class Dbfs(object):
    """Database browser implementation

    Args:
        dbutils (DBUtils): DBUtils object (for fs only)
    """

    def __init__(self, dbutils):
        self.dbutils = dbutils
        self.running = False
        self.path = None
        self.flist = None
        self.refresh = None
        self.path_view = None
        self.preview = None
        self.up = None

    def create(self, path="/", height="400px"):
        if self.running:
            print("dbfs browser already running. Use close() first")
            return
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
            VBox([HBox([self.refresh, self.up, self.path_view]), HBox([self.flist, self.preview]),])
        )

        self.update()
        self.running = True

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
        except:  # pylint: disable=bare-except
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
            "html",
            "csv",
            "txt",
            "sh",
            "sql",
            "py",
            "scala",
            "json",
            "jpg",
            "jpeg",
            "png",
            "gif",
        ]:
            ext = parts[-1].lower()
            filename = "/dbfs" + real_path
            # text = self.dbutils.fs.head(real_path)
            self.preview.clear_output()
            with self.preview:
                if ext == "html":
                    display(HTML(filename=filename))
                elif ext in ["py", "sh", "sql", "scala"]:
                    display(Code(filename=filename))
                elif ext in ["jpg", "jpeg", "png", "gif"]:
                    display(Image(filename=filename))
                elif ext == "md":
                    display(Markdown(filename=filename))
                elif ext == "csv":
                    df = pd.read_csv(filename)
                    display(df)
                else:
                    with open(filename, "r") as fd:
                        print(fd.read())

    def on_refresh(self, _):
        """Refresh handler

        Args:
            b (ipywidgets.Button): clicked button
        """
        self.update()

    def on_up(self, _):
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
            if len(change["new"]) > 0 and change["new"][-1] == "/":
                old_path = self.path
                self.path = new_path
                if not self.update():
                    self.path = old_path
            else:
                self.show_path(new_path)
                self.show_preview(new_path)

    def close(self):
        """Close view"""
        self.running = False
