import os
from collections import defaultdict
import platform
import random
import ssh_config
import sys
import time

if platform.platform(1, 1).split("-")[0] == 'Windows':
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
    if is_windows():
        option, index = pick(choices, message)
        return {tag: option}
    else:
        choice = [
            inquirer.List(tag,
                          message=message,
                          choices=choices)
        ]
        return inquirer.prompt(choice, theme=Dark())

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


