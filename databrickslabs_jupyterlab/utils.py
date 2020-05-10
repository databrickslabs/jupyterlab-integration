import os
import platform
import subprocess
import sys
import tempfile
from html import escape

import ssh_config

is_windows = platform.platform(1, 1).split("-")[0] == "Windows"


def bye(status=0):
    """Standard exit function
    
    Args:
        msg (str, optional): Exit message to be printed. Defaults to None.
    """
    if status != 0:
        print_error("\n=> Exiting")
    sys.exit(status)


def _print(color, *args):
    # Under Windows prompt_toolkit does not work with pytest
    # So add an environment variable check to switch to simple output
    if is_windows and (os.environ.get("PYTEST_CURRENT_TEST") is not None):
        print(*args)
    else:
        from prompt_toolkit import print_formatted_text, HTML
        from prompt_toolkit.styles import Style

        style = Style.from_dict({"error": "#ff0000", "ok": "#00ff00", "warning": "#ff00ff"})
        print_formatted_text(
            HTML(
                "<{color}>{message}</{color}>".format(color=color, message=escape(" ".join(args)))
            ),
            style=style,
        )


def print_ok(*args):
    _print("ok", *args)


def print_error(*args):
    _print("error", *args)


def print_warning(*args):
    _print("warning", *args)


def question(tag, message, choices):
    # Under Windows prompt_toolkit does not work with pytest
    # So only load questionary when this function is called - which is not used by automated tests
    import questionary
    from prompt_toolkit.styles import Style

    custom_style_fancy = Style(
        [
            ("answer", "fg:#f44336 bold"),  # submitted answer text behind the question
            ("highlighted", "fg:#f44336 bold",),  # pointed-at choice in select and checkbox prompts
        ]
    )

    answer = questionary.select(
        message, choices=choices, style=custom_style_fancy,
    ).ask()  # returns value of selection
    return {tag: answer}


def utf8_decode(text):
    if isinstance(text, str):
        return text

    try:
        return text.decode("utf-8")
    except:  # pylint: disable=bare-except
        # ok, let's replace the "bad" characters
        return text.decode("utf-8", "replace")


def execute(cmd):
    """Execute subprocess
    
    Args:
        cmd (list(str)): Command as list of cmd parts (e.g. ["ls", "-l"])
    """
    if is_windows and cmd[0] == "conda":
        cmd[0] = "conda.bat"

    try:
        # Cannot use encoding arg at the moment, since need to support python 3.5
        result = subprocess.run(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, check=False
        ).__dict__
        result["stderr"] = utf8_decode(result["stderr"])
        result["stdout"] = utf8_decode(result["stdout"])
        # print(result["returncode"])
        # print(result["stdout"])
        # print(result["stderr"])
        return result
    except Exception as ex:  # pylint: disable=broad-except
        print("%s; %s" % (type(ex), ex))
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
            print_error(str(result))
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
            for h in sc.hosts()
            if h.attributes().get("HostName", None) is not None
        }

    def get_dns(self, host_name):
        if self._get_mtime() > self.mtime:
            self.load()
        return self.hosts.get(host_name, None)
