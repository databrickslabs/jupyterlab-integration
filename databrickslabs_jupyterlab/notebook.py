import os
import sys

from IPython import get_ipython


class NotebookExit(BaseException):
    pass


class Notebook:
    def __init__(self):
        self.ipython = get_ipython()
        self._showtraceback = self.ipython._showtraceback
        self.ipython._showtraceback = self._exception_handler

    def run(self, notebook):
        path, ext = os.path.splitext(notebook)
        if not ext in [".ipynb", ".py", ""]:
            print("Only notebooks with ending .ipynb or python files with ending .py supported")
        else:
            if path.startswith("dbfs:"):
                path = path[5:]
            path = "/dbfs/" + path.strip("/") + ext
            if ext == "":
                if os.path.exists(path + ".ipynb"):
                    path = path + ".ipynb"
                elif os.path.exists(path + ".py"):
                    path = path + ".py"
            if os.path.exists(path):
                print("Running '{}'".format(path))
                return self.ipython.magic("run %s" % path)
            else:
                print("Error, '{}' does not exist".format(path))

    def _exception_handler(self, exception_type, exception, traceback):
        if exception_type == NotebookExit:
            print("Notebook exited: %s" % (exception), file=sys.stderr)
        else:
            self._showtraceback(exception_type, exception, traceback)

    def exit(self, msg):
        raise NotebookExit(msg)
