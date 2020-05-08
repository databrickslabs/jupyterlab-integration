import json
import logging
import nbformat
import os
import subprocess

import requests

from pytest_httpserver import HTTPServer

from helpers import get_profile, EXE, is_aws

from databrickslabs_jupyterlab.local import get_db_config
from databrickslabs_jupyterlab import __version__


class TestEnd2End:
    def setup_method(self):
        self.profile = get_profile()
        self.host, self.token = get_db_config(self.profile)
        self.log = logging.getLogger("TestEnd2End")
        self.log.info("Using %s on %s", EXE, ("AWS" if is_aws() else "Azure"))

    def test_dj_p(self):
        result = subprocess.check_output([EXE, self.profile, "-p"])
        profiles = [p for p in result.decode("utf-8").split("\n") if self.profile in p]
        assert len(profiles) == 1
        p, host, status = profiles[0].split()
        assert p == self.profile
        assert host == self.host
        assert status == "OK"

    # dj -W
    def test_dj_W(self):
        result = subprocess.check_output([EXE, self.profile, "-W"])
        lines = result.decode("utf-8").strip().split("\n")
        assert len(lines) == 2
        libs = json.loads(lines[1].replace("'", '"'))
        assert len(libs) == 31
        assert "pandas" in libs

    # dj -B
    def test_dj_B(self):
        result = subprocess.check_output([EXE, self.profile, "-B"])
        lines = result.decode("utf-8").strip().split("\n")
        assert len(lines) == 2
        libs = json.loads(lines[1].replace("'", '"'))
        assert len(libs) == 143
        assert "databrickslabs-jupyterlab" in libs

    # dj -v
    def test_dj_v(self):
        result = subprocess.check_output([EXE, self.profile, "-v"])
        version = result.decode("utf-8").strip()
        assert version == __version__

    def test_dj_n(self):
        result = subprocess.check_output(
            [
                EXE,
                "-n",
                "https://docs.databricks.com/_static/notebooks/getting-started/popvspricemultichart.html",
            ]
        )

        with open("popvspricemultichart.ipynb", "r") as fd:
            notebook = fd.read()
        js = nbformat.reads(notebook, as_version=4)
        assert js["cells"][0].source == "**Downloaded by Databrickslabs Jupyterlab**"

        os.unlink("popvspricemultichart.ipynb")

    def test_dj_n_local(self, httpserver: HTTPServer):
        data = open("./data/test-db-jlab.html", "r").read()
        httpserver.expect_request("/test-db-jlab.html").respond_with_data(data)

        result = subprocess.check_output([EXE, "-n", httpserver.url_for("/test-db-jlab.html")])
        assert result.decode("utf-8").startswith("*** experimental ***")
        assert os.path.exists("test-db-jlab.ipynb")

        with open("test-db-jlab.ipynb", "r") as fd:
            notebook = fd.read()
        js = nbformat.reads(notebook, as_version=4)

        self.log.info(json.dumps(js))

        assert js["cells"][0]["cell_type"] == "markdown"
        assert js["cells"][0]["source"] == "**Downloaded by Databrickslabs Jupyterlab**"

        assert js["cells"][1]["cell_type"] == "code"
        assert js["cells"][1]["source"] == "a = 42"

        assert js["cells"][2]["cell_type"] == "code"
        assert js["cells"][2]["source"] == "%%sql\n\nuse default"

        assert js["cells"][3]["cell_type"] == "code"
        assert js["cells"][3]["source"] == "%%sql\n\nselect * \nfrom iris\nwhere speal_width > 0.8"

        assert js["cells"][4]["cell_type"] == "code"
        assert js["cells"][4]["source"] == "%%sql\n\n\nuse default"

        assert js["cells"][5]["cell_type"] == "code"
        assert js["cells"][5]["source"] == "%%sql\n\nselect * \nfrom iris\nwhere speal_width < 0.8"

        assert js["cells"][6]["cell_type"] == "code"
        assert js["cells"][6]["source"] == "%%scala\n\nval result = sc.range(0,10).collect()"

        os.unlink("test-db-jlab.ipynb")
