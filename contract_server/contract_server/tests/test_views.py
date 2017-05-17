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

    def fake_deploy_contracts(tx_hash):
        return True

    def fake_deploy_contracts_failed(tx_hash):
        return False

    def fake_check_watch(tx_hash, multisig_address):
        return True

    def test_address_notified_bad_request(self):
        self.response = self.client.post(self.url, {})
        self.assertEqual(self.response.status_code, httplib.NOT_ACCEPTABLE)

    @mock.patch("evm_manager.deploy_contract_utils.deploy_contracts", fake_deploy_contracts)
    @mock.patch("events.state_log_utils.check_watch", fake_check_watch)
    def test_address_notified(self):
        self.response = self.client.post(self.url, self.sample_form)
        self.assertEqual(self.response.status_code, httplib.OK)

    def test_wrong_apiversion(self):
        self.sample_form['apiVersion'] = 'wrong_api_version'
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.NOT_ACCEPTABLE)
