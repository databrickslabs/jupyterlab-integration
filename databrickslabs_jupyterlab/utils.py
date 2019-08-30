import os
from collections import defaultdict
from pexpect import pxssh
import random
import ssh_config
import subprocess
import sys
import time

from inquirer.themes import Default, term


# class Ssh:
#     def __init__(self, ssh_config="~/.ssh/config"):
#         self.ssh_config = os.path.expanduser(ssh_config)
#         self.ssh = defaultdict(lambda: None)

#     def _split_lines(self, result):
#         return result.decode("utf-8").strip().split("\r\n")[1:]

#     def execute(self, host, cmd):
#         if self.ssh[host] is None:
#             success = False
#             delays = [2, 4, 8]
#             for retry in range(3):
#                 print("   => Connecting to %s via ssh (%d)" % (host, retry + 1))
#                 try:
#                     self.ssh[host] = pxssh.pxssh(options={"StrictHostKeyChecking": "no"})
#                     self.ssh[host].login(host, quiet=False, ssh_config=self.ssh_config)
#                     success = True
#                     break
#                 except:
#                     delay = round(random.random(), 2) + delays[retry]
#                     print_warning("   Failed to log into %s, waiting %3.1f seconds" % (host, delay))
#                     time.sleep(delay)

#             if success:
#                 print_ok("   => OK")
#             else:
#                 print_error("   => Error")
#                 return {"exit_code": -1, "result": None}

#         self.ssh[host].sendline(cmd)
#         self.ssh[host].prompt()
#         result = self._split_lines(self.ssh[host].before)
#         self.ssh[host].sendline('echo $?')
#         self.ssh[host].prompt()
#         exit_code = self._split_lines(self.ssh[host].before)
#         try:
#             exit_code = int(exit_code[0])
#         except:
#             pass
#         if exit_code != 0: 
#             print_error("   => Remote command failed")
#         return {"exit_code": exit_code, "result": result}

#     def close(self, host):
#         if self.ssh[host] is not None:
#             print("   => Closing ssh connection to %s" % host)
#             self.ssh[host].logout()
#             self.ssh[host] = None


def run(cmd):
    """Run a shell command
    
    Args:
        cmd (str): shell command
    """
    try:
        subprocess.run(cmd)
    except:
        print_error("Error running: %s" % cmd)
        bye(1)


def bye(status=0):
    """Standard exit function
    
    Args:
        msg (str, optional): Exit message to be printed. Defaults to None.
    """
    if status != 0:
        print_error("\n=> Exiting")
    sys.exit(status)


class Dark(Default):
    """Dark Theme for inquirer"""
    def __init__(self):
        super().__init__()
        self.List.selection_color = term.cyan


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


