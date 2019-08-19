import unittest

class TestRemoteMethods(unittest.TestCase):

    def setUp(self):
        self.host, self.token = get_db_config(PROFILE)
        self.cluster_id = CLUSTER_ID
        self.rest = Rest()

    def test_create_context(self):
        data = {"language": "python", "clusterId": self.cluster_id}
        response = self.rest.post(self.host, "1.2", "contexts/create", data=data, token=self.token)
        self.assertIsNotNone(response.get("id", None))
        self.context_id = response.get("id")
