#   Copyright 2019 Bernhard Walter
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os

import requests


class Rest(object):
    @classmethod
    def _json(cls, response, key=None):
        try:
            value = response.json()
            if key is not None:
                value = value[key]
            return value
        except:
            print("Error", response.text)
            return None

    @classmethod
    def get(cls, url, api_version, path, token):
        full_url = os.path.join(url, "api/%s" % api_version, path)
        response = requests.get(full_url, auth=("token", token))
        return Rest._json(response)

    @classmethod
    def post(cls, url, api_version, path, token, json=None, data=None, files=None, key=None):
        full_url = os.path.join(url, "api/%s" % api_version, path)
        response = requests.post(full_url, json=json, data=data, files=files, auth=("token", token))
        return Rest._json(response, key)


class Context(object):

    instance = None

    class __Context(object):
        def __init__(self, url, clusterId, token):
            self.token = token
            self.url = url
            self.clusterId = clusterId
            self.id = None

        def create(self):
            data = {"language": "python", "clusterId": self.clusterId}
            self.id = Rest.post(self.url, "1.2", "contexts/create", data=data, token=self.token, key="id")
            return self.id

        def status(self):
            path = "contexts/status?contextId=%s&clusterId=%s" % (self.id, self.clusterId)
            return Rest.get(self.url, "1.2", path, token=self.token)

        def destroy(self):
            data = {"contextId": self.id, "clusterId": self.clusterId}
            return Rest.post(self.url, "1.2", "contexts/destroy", data=data, token=self.token)

    def __init__(self, url=None, clusterId=None, token=None):
        if not Context.instance:
            Context.instance = Context.__Context(url, clusterId, token)

    def __getattr__(self, name):
        return getattr(self.instance, name)


class Command(object):
    def __init__(self, url, clusterId, token):
        self.token = token
        self.url = url
        self.clusterId = clusterId
        self.context = Context(url, clusterId, token)
        self.context.create()

    def execute(self, command):
        data = {"language": "python", "contextId": self.context.id, "clusterId": self.clusterId}
        files = {"command": command}
        self.commandId = Rest.post(self.url,
                                   "1.2",
                                   "commands/execute",
                                   data=data,
                                   files=files,
                                   token=self.token,
                                   key="id")
        return self.commandId

    def status(self, commandId=None):
        cmdId = commandId or self.commandId
        path = "commands/status?commandId=%s&contextId=%s&clusterId=%s" % (cmdId, self.context.id, self.clusterId)
        return Rest.get(self.url, "1.2", path, token=self.token)


class Clusters(object):
    def __init__(self, url, token):
        self.url = url
        self.token = token

    def status(self, cluster_id):
        result = Rest.get(self.url, "2.0", "clusters/get?cluster_id=%s" % cluster_id, token=self.token)
        return result

    def start(self, cluster_id):
        data = {"cluster_id": cluster_id}
        result = Rest.post(self.url, "2.0", "clusters/start", json=data, token=self.token)
        return result


class Libraries(object):
    def __init__(self, url, token):
        self.url = url
        self.token = token

    def status(self, cluster_id):
        result = Rest.get(self.url, "2.0", "libraries/cluster-status?cluster_id=%s" % cluster_id, token=self.token)
        return result
