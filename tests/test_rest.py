import json
import unittest

from databrickslabs_jupyterlab.remote import get_db_config
from databrickslabs_jupyterlab.rest import Rest, DatabricksApiException

PROFILE = "demo"
CLUSTER_ID = "0806-143104-skirt84"

class Response:
    def __init__(self, text):
        self.text = text
    
    def json(self):
        return json.loads(self.text)
        
class TestRestMethods(unittest.TestCase):
    
    def setUp(self):
        self.host, self.token = get_db_config(PROFILE)
        self.cluster_id = CLUSTER_ID
        self.rest = Rest()

    def test_get_ok(self):
        response = self.rest.get(self.host, "2.0", "clusters/get?cluster_id=%s" % self.cluster_id, token=self.token)
        self.assertEqual(response.get("cluster_id"), CLUSTER_ID)

    def test_get_wrong_path(self):
        with self.assertRaises(DatabricksApiException) as ex:
            self.rest.get(self.host, "2.0", "cluster/get?cluster_id=%s" % self.cluster_id, token=self.token)
        message = json.loads(ex.exception.error_message)
        self.assertEqual(message["error_code"], "ENDPOINT_NOT_FOUND")

    def test_get_wrong_parameter(self):
        with self.assertRaises(DatabricksApiException) as ex:
            self.rest.get(self.host, "2.0", "clusters/get?clusters_id=%s" % self.cluster_id, token=self.token)
        message = json.loads(ex.exception.error_message)
        self.assertEqual(message["error_code"], "INVALID_PARAMETER_VALUE")

    def test_get_wrong_host(self):
        with self.assertRaises(DatabricksApiException) as ex:
            self.rest.get(self.host + "X", "2.0", "clusters/get?clusters_id=%s" % self.cluster_id, token=self.token)
        message = ex.exception.error_message
        self.assertIn("[Errno 8]" , message)

    def test_json_ok(self):
        response = Response('{"id": 123}')
        j = self.rest._json(response)
        self.assertIsNotNone(j.get("id", None))

    def test_json_broken(self):
        with self.assertRaises(DatabricksApiException) as ex:
            response = Response('{"id": 123, 3}')
            self.rest._json(response)

    def test_json_text(self):
        with self.assertRaises(DatabricksApiException) as ex:
            response = Response('abcdef gh')
            self.rest._json(response)
