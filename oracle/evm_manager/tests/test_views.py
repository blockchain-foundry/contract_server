import json
import mock
try:
    import http.client as httplib
except:
    import httplib
from django.test import TestCase
from ..models import StateInfo


class CheckUpdateTestCase(TestCase):
    def setUp(self):
        StateInfo.objects.create(
            multisig_address='3LP9zszUXKQQox6EwZZEMKbQ6323tqGLLH',
            latest_tx_time=1000,
            latest_tx_hash='091c6f6100000000000000000000000000000000000000000000000000000003'
        )
        self.url = '/states/checkupdate/{multisig_address}/{tx_hash}'
        self.tx_hash = '091c6f6100000000000000000000000000000000000000000000000000000003'
        self.tx_hash_new = '091c6f6100000000000000000000000000000000000000000000000000000002'
        self.tx_hash_old = '091c6f6100000000000000000000000000000000000000000000000000000004'
        self.multisig_address = '3LP9zszUXKQQox6EwZZEMKbQ6323tqGLLH'
        self.wrong_addr = '3LP9zszUXKQQox6EwZZEMKbQ6323tqGLLHWRONG'
        self.sample_tx = {'blocktime': 1000, 'time': 1000}
        self.sample_txs = {
            'txs': [
                {'hash': '091c6f6100000000000000000000000000000000000000000000000000000003', 'time': 1000},
                {'hash': '091c6f6100000000000000000000000000000000000000000000000000000004', 'time': 1000},
                {'hash': '091c6f6100000000000000000000000000000000000000000000000000000005', 'time': 1000},
            ]
        }

    def tearDown(self):
        StateInfo.objects.all().delete()

    @mock.patch('evm_manager.views.get_tx')
    @mock.patch('evm_manager.views.get_multisig_address')
    @mock.patch('gcoinbackend.core.get_txs_by_address')
    def test_check_update(self, mock_txs_by_address, mock_multisig_address, mock_tx):
        mock_multisig_address.return_value = self.multisig_address
        mock_tx.return_value = self.sample_tx
        mock_txs_by_address.return_value = self.sample_txs

        response = self.client.get(self.url.format(
            multisig_address=self.multisig_address, tx_hash=self.tx_hash))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertEqual(data.get('data').get('completed'), True)

    @mock.patch('evm_manager.views.get_multisig_address')
    def test_wrong_multisig_addr(self, mock_multisig_address):
        mock_multisig_address.return_value = None

        response = self.client.get(self.url.format(
            multisig_address=self.wrong_addr, tx_hash=self.tx_hash))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data.get('data').get('completed'), False)

    @mock.patch('evm_manager.views.get_tx')
    @mock.patch('evm_manager.views.get_multisig_address')
    @mock.patch('gcoinbackend.core.get_txs_by_address')
    def test_tx_hash_with_same_time(self, mock_txs_by_address, mock_multisig_address, mock_tx):
        mock_multisig_address.return_value = self.multisig_address
        mock_tx.return_value = self.sample_tx
        mock_txs_by_address.return_value = self.sample_txs

        response = self.client.get(self.url.format(
            multisig_address=self.multisig_address, tx_hash=self.tx_hash_new))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data.get('data').get('completed'), False)

        response = self.client.get(self.url.format(
            multisig_address=self.multisig_address, tx_hash=self.tx_hash_old))
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data.get('data').get('completed'), True)
