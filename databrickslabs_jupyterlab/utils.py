import os
from collections import defaultdict
import platform
import random
import subprocess
import sys
import tempfile
import time

import ssh_config

is_windows = platform.platform(1, 1).split("-")[0] == "Windows"

if is_windows:
    from pick import pick
else:
    from inquirer import prompt
    from inquirer.themes import Default, term

    class Dark(Default):
        """Dark Theme for inquirer"""
        def __init__(self):
            super().__init__()
            self.List.selection_color = term.cyan


def is_windows():
    return platform.platform(1, 1).split("-")[1] == 'Windows'

def bye(status=0):
    """Standard exit function
    
    Args:
        msg (str, optional): Exit message to be printed. Defaults to None.
    """
    if status != 0:
        print_error("\n=> Exiting")
    sys.exit(status)


class Colors:
    ERROR = '\033[91m'
    OK = '\033[92m'
    WARNING = '\033[93m'
    RESET = '\033[0m'


def _print(color, *args):
    print(color, end="")
    print(*args, end="")
    print(Colors.RESET)


def print_ok(*args):
    _print(Colors.OK, *args)


def print_error(*args):
    _print(Colors.ERROR, *args)


def print_warning(*args):
    _print(Colors.WARNING, *args)

def question(tag, message, choices):
    if is_windows:
        option, _ = pick(choices, message)
        return {tag: option}
    else:
        choice = [
            inquirer.List(tag,
                          message=message,
                          choices=choices)
        ]
        return inquirer.prompt(choice, theme=Dark())


def utf8_decode(text):
    if isinstance(text, str):
        return text

    try:
        return text.decode("utf-8")
    except:
        # ok, let's replace the "bad" characters
        return text.decode("utf-8", "replace")


def execute(cmd):
    """Execute subprocess
    
    Args:
        cmd (list(str)): Command as list of cmd parts (e.g. ["ls", "-l"])
    """
    print(cmd)
    try:
        # Cannot use encoding arg at the moment, since need to support python 3.5
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE).__dict__
        result["stderr"] = utf8_decode(result["stderr"])
        result["stdout"] = utf8_decode(result["stdout"])
        return result
    except Exception as ex:
        return {"args": cmd, "returncode": -1, "stdout": "", "stderr": str(ex)}


def execute_script(script, success_message, error_message):
    with tempfile.TemporaryDirectory() as tmpdir:
        script_name = "db_jlab_script.bat" if is_windows else "db_jlab_script.sh"

        script_file = os.path.join(tmpdir, script_name)
        with open(script_file, "w") as fd:
            fd.write(script)

        cmd = [script_file] if is_windows else ["bash", script_file]

        result = execute(cmd)
        if result["returncode"] != 0:
            print_error(error_message)
            sys.exit(1)
        else:
            print_ok(success_message)


class SshConfig:
    def __init__(self):
        self.config_file = os.path.expanduser("~/.ssh/config")
        self.load()

    def _get_mtime(self):
        return os.stat(self.config_file).st_mtime

    def load(self):
        self.mtime = self._get_mtime()
        sc = ssh_config.SSHConfig.load(self.config_file)
        self.hosts = {
            h.name: h.attributes()["HostName"]
            for h in sc.hosts() if h.attributes().get("HostName", None) is not None
        }

    def get_dns(self, host_name):
        if self._get_mtime() > self.mtime:
            self.load()
        return self.hosts.get(host_name, None)


