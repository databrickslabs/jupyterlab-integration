import os
import subprocess
import tempfile

import inquirer
from inquirer.themes import Default, term

import databrickslabs_jupyterlab
from databrickslabs_jupyterlab.remote import Dark


import conda.cli.python_api as Conda
import sys


def get_env_file(module_path):
    def expand(f):
        return os.path.join(module_path, "dbr-env-file-plugins", f)
    
    env_files = os.listdir(os.path.join(module_path, "env_files"))

    choice = [
        inquirer.List('env_id',
                    message='Which environment do you want to mirror?',
                    choices=[os.path.splitext(env_file)[0] for env_file in env_files])
    ]
    answer = inquirer.prompt(choice, theme=Dark())
    env_file = answer["env_id"] + ".yml"

    return env_file

def install_env(enf_file, env_name):
    try:
        (stdout_str, stderr_str, return_code_int) = Conda.run_command(
            Conda.Commands.INSTALL, 
            ["env", "create", "-n", env_name, "-f", env_file],
            use_exception_handler=True,
            stdout=sys.stdout, 
            stderr=sys.stderr)
        print(stdout_str, stderr_str, return_code_int)
    except:
        print("Error while installing conda environment")
        sys.exit(1)

def install_labextions():
    pass

def install(env_name):
    module_path = os.path.dirname(databricks_jupyterlab.__file__)
    env_file = get_env_file(module_path)
    install_env(env_file, env_name)
    os.unlink(env_file)
