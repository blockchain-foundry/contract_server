import json
import mock
import requests
try:
    import http.client as httplib
except:
    import httplib
from django.test import TestCase
from oracles.models import Contract, Oracle


class CheckUpdateTestCase(TestCase):
    def setUp(self):
        oracle1 = Oracle.objects.create(name="test1", url="0.0.0.0:123")
        oracle2 = Oracle.objects.create(name="test2", url="0.0.0.0:124")
        contract = Contract.objects.create(
            multisig_address='3LP9zszUXKQQox6EwZZEMKbQ6323tqGLLH',
            least_sign_number=2,
            color_id=1,
            amount=0,
        )
        contract.oracles.add(oracle1)
        contract.oracles.add(oracle2)
        self.url = '/states/checkupdate/{multisig_address}/{tx_hash}'
        self.tx_hash = '091c6f6100000000000000000000000000000000000000000000000000000003'
        self.tx_hash_new = '091c6f6100000000000000000000000000000000000000000000000000000002'
        self.tx_hash_old = '091c6f6100000000000000000000000000000000000000000000000000000004'
        self.multisig_address = '3LP9zszUXKQQox6EwZZEMKbQ6323tqGLLH'
        self.multisig_address_wrong = '3LP9zszUXKQQox6EwZZEMKbQ6323tqGLLHWRONG'
        self.oracle_json_true = {"data": {"completed": True}}
        self.oracle_json_false = {"data": {"completed": False}}

    def tearDown(self):
        Oracle.objects.all().delete()
        Contract.objects.all().delete()

    @mock.patch('evm_manager.views.requests')
    def test_check_update(self, mock_requests):
        mock_requests.get.return_value = mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.oracle_json_true

        response = self.client.get(self.url.format(
            multisig_address=self.multisig_address, tx_hash=self.tx_hash))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertEqual(data.get('data').get('completed'), 2)

    @mock.patch('evm_manager.views.requests')
    def test_request_timeout(self, mock_requests):
        def timeout(*arg, **kwargs):
            raise requests.exceptions.Timeout

        mock_requests.get.side_effect = timeout

        response = self.client.get(self.url.format(
            multisig_address=self.multisig_address, tx_hash=self.tx_hash))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertEqual(data.get('data').get('completed'), 0)

    def test_wrong_multisig_addr(self):
        response = self.client.get(self.url.format(
            multisig_address=self.multisig_address_wrong, tx_hash=self.tx_hash))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data.get('error')[0].get('code'), httplib.BAD_REQUEST)
