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
        if os.path.splitext(notebook) != ".ipynb":
            notebook += ".ipynb"
        return self.ipython.magic("run %s" % notebook)

    def _exception_handler(self, exception_type, exception, traceback):
        if exception_type == NotebookExit:
            print("Notebook exited: %s" % (exception), file=sys.stderr)
        else:
            self._showtraceback(exception_type, exception, traceback)

    def exit(self, msg):
        raise NotebookExit(msg)
