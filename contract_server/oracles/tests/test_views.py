import json
from django.test import TestCase

from oracles.models import Oracle

try:
    import http.client as httplib
except ImportError:
    import httplib


class RegisterOracleCase(TestCase):
    def setUp(self):
        self.url = "/oracles/register/"

        self.sample_form = {
            "name": "test_oracle",
            "url": 'http:127.0.0.1:33006',
            "apiVersion": "0.3.0"
        }

    def fake_clear_evm_accouts(multisig_address):
        return {"addresses": multisig_address, "evm_accounts_of_addresses": "000000000000000000000000000000001234", "payouts": 0, "before_balance": 0, "after_balance": 0}

    def fake_deploy_contracts(tx_hash):
        return True

    def fake_deploy_contracts_failed(tx_hash):
        return False

    def fake_check_watch(tx_hash, multisig_address):
        return True

    def test_register_oracle_success(self):
        self.response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(self.response.content.decode('utf-8'))
        self.assertEqual(self.response.status_code, httplib.OK)
        self.assertIn("Add oracle successfully", json_data['data']['message'])

    def test_wrong_apiversion(self):
        self.sample_form['apiVersion'] = 'wrong'
        self.response = self.client.post(self.url, self.sample_form)
        self.assertEqual(self.response.status_code, httplib.NOT_ACCEPTABLE)


class Oraclelist(TestCase):
    def setUp(self):
        self.url = "/oracles/"
        test_db = Oracle(name="test_oracle", url="http://127.0.0.1:33006")
        test_db.save()

    def fake_clear_evm_accouts(multisig_address):
        return {"addresses": multisig_address, "evm_accounts_of_addresses": "000000000000000000000000000000001234", "payouts": 0, "before_balance": 0, "after_balance": 0}

    def fake_deploy_contracts(tx_hash):
        return True

    def fake_deploy_contracts_failed(tx_hash):
        return False

    def fake_check_watch(tx_hash, multisig_address):
        return True

    def test_register_oracle_success(self):
        self.response = self.client.get(self.url)
        self.assertEqual(self.response.status_code, httplib.OK)
