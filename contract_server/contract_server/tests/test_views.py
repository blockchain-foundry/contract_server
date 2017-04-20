import json
import mock
from django.test import TestCase
from django.conf import settings

try:
    import http.client as httplib
except ImportError:
    import httplib


class AddressNotifiedCase(TestCase):
    def setUp(self):
        self.url = "/addressnotify/339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4"

        self.sample_form = {
            "tx_hash": "1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq",
            "subscription_id": '1',
            "notification_id": '2',
            "apiVersion": settings.API_VERSION,
        }

    def fake_clear_evm_accounts(multisig_address):
        return {"addresses": multisig_address, "evm_accounts_of_addresses": "000000000000000000000000000000001234", "payouts": 0, "before_balance": 0, "after_balance": 0}

    def fake_deploy_contracts(tx_hash):
        return True

    def fake_deploy_contracts_failed(tx_hash):
        return False

    def fake_check_watch(tx_hash, multisig_address):
        return True

    def test_address_notified_bad_request(self):
        self.response = self.client.post(self.url, {})
        self.assertEqual(self.response.status_code, httplib.NOT_ACCEPTABLE)

    @mock.patch("evm_manager.deploy_contract_utils.deploy_contracts", fake_deploy_contracts_failed)
    @mock.patch("contract_server.cashout.clear_evm_accounts", fake_clear_evm_accounts)
    def test_address_notified_failed(self):
        self.response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(self.response.content.decode('utf-8'))
        self.assertEqual(self.response.status_code, httplib.OK)
        self.assertIn("State-Update failed", json_data['data']['status'])

    @mock.patch("evm_manager.deploy_contract_utils.deploy_contracts", fake_deploy_contracts)
    @mock.patch("events.state_log_utils.check_watch", fake_check_watch)
    @mock.patch("contract_server.views.clear_evm_accounts", fake_clear_evm_accounts)
    def test_address_notified_success(self):
        self.response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(self.response.content.decode('utf-8'))
        self.assertEqual(self.response.status_code, httplib.OK)
        self.assertIn("State-Update completed", json_data['data']['status'])

    def test_wrong_apiversion(self):
        self.sample_form['apiVersion'] = 'wrong_api_version'
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.NOT_ACCEPTABLE)
