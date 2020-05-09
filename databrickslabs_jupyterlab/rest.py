import time
from urllib.parse import urljoin
import xml.etree.ElementTree

import requests

from databrickslabs_jupyterlab._version import __version__


class DatabricksApiException(Exception):
    """Exception class for Databricks API errors
    
    Args:
        status_code (int): HTTP status code
        error_code (int): Error specific code
        error_message (str): Error message

    Attributes:
        status_code (int): HTTP status code
        error_code (int): Error specific code
        error_message (str): Error message
    """

    def __init__(self, status_code, error_code, error_message):
        super().__init__()
        self.status_code = status_code
        self.error_code = error_code
        self.error_message = error_message


class Rest(object):
    """Rest class to execute REST get and post calls.
    JSON Results will automatically be converted to dicts
    """

    headers = {"User-Agent": "databrickslabs-jupyterlab-%s" % __version__}

    def _rest_error(self, status_code, error_code, message):
        """Create a stabdard REST error message
        
        Args:
            status_code (str): HTTP status code
            error_code (str): Error code
            message (str): Error message
        
        Returns:
            dict: Dictionary with status_code, error_code and message
        """
        return {"status_code": status_code, "error_code": error_code, "message": message}

    def _remove_tags(self, text):
        """Very simple routine to get rid of HTML tags of error responses
        
        Args:
            text (str): HTML error message
        
        Returns:
            str: The error message without HTML tags
        """
        try:
            result = "".join(xml.etree.ElementTree.fromstring(text).itertext()).replace(
                "\n\n", "\n"
            )
        except:  # pylint: disable=bare-except
            result = text
        return result

    def _json(self, response):
        """Convert a JSON response to dict.
        
        Args:
            response (object): Response object as returned by requests
        
        Returns:
            dict: A dict representing the JSON input or None in error case
        """
        try:
            return response.json()
        except Exception:
            raise DatabricksApiException(
                403, 3, "Invalid json message: %s" % self._remove_tags(response.text)
            )

    def get(self, url, api_version, path, token):
        """REST GET function
        
        Args:
            url (str): URL for the request
            api_version (str): "1.2" (command execution) or "2.0" for all other API calls
            path (str): Additional path for the request
            token (str): Authentication token
        
        Returns:
            dict: A dict representing the JSON result of the call 
                  or in error case with keys status_code, error_code, message.
        """
        full_url = urljoin(url, "api/%s/%s" % (api_version, path.lstrip("/")))
        try:
            response = requests.get(full_url, auth=("token", token), headers=self.headers)
        except Exception as ex:
            raise DatabricksApiException(0, 5, str(ex))
        if response.status_code in (200, 201):
            return self._json(response)
        else:
            raise DatabricksApiException(response.status_code, 1, self._remove_tags(response.text))

    def post(self, url, api_version, path, token, json=None, data=None, files=None):
        """REST POST function
        
        Args:
            url (str): URL for the request
            api_version (str): "1.2" (command execution) or "2.0" for all other API calls
            path (str): Additional path for the request
            token (str): Authentication token
            json (str, optional): json data to send in the body of the request. Defaults to None.
            data ([type], optional): Dictionary, list of tuples, bytes, or file-like object to send
                                     in the body of the request. Defaults to None.
            files ([type], optional): Files to send with the request. Defaults to None.
            key (str, optional): Key to select from the converted JSON string. Defaults to None.
        
        Returns:
            dict: A dict representing the JSON result of the call 
            or in error case with keys status_code, error_code, message.
        """
        full_url = urljoin(url, "api/%s/%s" % (api_version, path.lstrip("/")))
        try:
            response = requests.post(
                full_url,
                json=json,
                data=data,
                files=files,
                auth=("token", token),
                headers=self.headers,
            )
        except Exception as ex:
            raise DatabricksApiException(0, 5, str(ex))
        if response.status_code in (200, 201):
            return self._json(response)
        else:
            raise DatabricksApiException(response.status_code, 2, self._remove_tags(response.text))


class Context(Rest):
    """Execution Context for Databricks

    Context is derived from ``Rest`` and uses Databricks REST API 1.2 
    
    Args:
        url (str): Databricks workspace URL
        cluster_id (str): Cluster ID
        token (str): Authentication token

    Attributes:
        url (str): Databricks workspace URL
        cluster_id (str): Cluster ID
        token (str): Authentication token
        id (str): Context ID
    """

    def __init__(self, url, cluster_id, token, language="python"):
        self.token = token
        self.url = url
        self.cluster_id = cluster_id
        self.language = language
        self.id = None

    def create(self):
        """Create an Execution Context
        
        Returns:
            str: Context ID
        """
        data = {"language": self.language, "clusterId": self.cluster_id}
        response = self.post(self.url, "1.2", "contexts/create", data=data, token=self.token)
        self.id = response.get("id", None)
        if self.id is None:
            raise DatabricksApiException(403, 4, "Context ID missing")

    def status(self):
        """Get status of Execution Context
        
        Returns:
            dict: Dictionary with context id and status
        """
        path = "contexts/status?contextId=%s&clusterId=%s" % (self.id, self.cluster_id)
        return self.get(self.url, "1.2", path, token=self.token)

    def destroy(self):
        """Destroy Execution Context
        
        Returns:
            dict: Dictionary with context id
        """
        data = {"contextId": self.id, "clusterId": self.cluster_id}
        return self.post(self.url, "1.2", "contexts/destroy", data=data, token=self.token)


class Command(Rest):
    """Command execution on Databricks

    Command is derived from ``Rest`` and uses Databricks REST API 1.2 
        
    Args:
        url (str): Databricks workspace URL
        clusterId (str): Cluster ID
        token (str): Authentication token

    Attributes:
        url (str): Databricks workspace URL
        cluster_id (str): Cluster ID
        token (str): Authentication token
        context (Context): The Execution Context for the commands
    """

    def __init__(self, url, cluster_id, token, language="python", scala_context_id=None):
        self.token = token
        self.url = url
        self.cluster_id = cluster_id
        self.language = language

        self.context = Context(url, cluster_id, token, language)
        if scala_context_id is None:
            self.context.create()
        else:
            self.context.id = scala_context_id

    def execute(self, command, full_result=False):
        """Execute a python command under the given Execution Context
        
        Args:
            command (str): One line of python code
        
        Returns:
            str: The ID of the command
        """
        data = {
            "language": self.language,
            "contextId": self.context.id,
            "clusterId": self.cluster_id,
        }
        files = {"command": command}
        response = self.post(
            self.url, "1.2", "commands/execute", data=data, files=files, token=self.token
        )
        command_id = response.get("id", None)
        if command_id is None:
            raise DatabricksApiException(403, 4, "Command ID missing")

        finished = False
        count = 0
        while not finished:
            print(".", end="", flush=True)
            count += 1
            time.sleep(0.5)
            result = self.status(command_id)
            finished = result["status"] == "Finished"
        print("\r", " " * (count + 1))

        if result["results"]["resultType"] == "error":
            if full_result:
                return (-1, result)
            else:
                return (-1, result["results"]["cause"])
        else:
            if full_result:
                return (0, result)
            else:
                return (0, result["results"]["data"])

    def status(self, command_id):
        """Check the status of the command execution
        
        Args:
            commandId (str): The command ID
        
        Returns:
            dict: Dictionary with context id and status
        """
        path = "commands/status?commandId=%s&contextId=%s&clusterId=%s" % (
            command_id,
            self.context.id,
            self.cluster_id,
        )
        return self.get(self.url, "1.2", path, token=self.token)

    def close(self):
        self.context.destroy()
