import json
import mock
try:
    import http.client as httplib
except ImportError:
    import httplib

from django.test import TestCase

from app.models import Proposal, Keystore


class ProposeTest(TestCase):

    def setUp(self):
        super(ProposeTest, self).setUp()
        self.url = '/proposals/'
        self.sample_form = {
            'source_code': 'fake_source_code'
        }

    def test_proposal_without_condition(self):
        response = self.client.post(self.url, self.sample_form)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertNotEqual(data.get('public_key'), None)


class SignTest(TestCase):

    def setUp(self):
        super(SignTest, self).setUp()
        self.url = '/sign/'
        self.sample_form = {
            'raw_tx': '01000000020c1699137178f668a90133ac58533b20a7d304aea30bd50e247dc500caf669f60000000017a91433a40fbbfa650a3370133ece5e055d697276727987ffffffffffcb2af7bbc6506be46b7f0bfe20f1f060dbf856b172c63b671cf842c64f85ce0000000017a91433a40fbbfa650a3370133ece5e055d697276727987ffffffff0100e1f505000000001976a914ad07c94ce95ac2f968b031753faefdb8197701e988ac010000000000000000000000',
            'script': '5241048cfd6643a92b2681a753521c056838f3d104a91af3bf37104dba698b4c75c5025ab25d96b600fef2d105b3e005e6e4ae2c234a58f54a8683762b05fd59935052410446e808db7643ad742e72f88f6c19e526b85fd1600e10b4e2c26e6f370e0868f0453306273fe8c75b19ba5c4796e26707bfd78d7c54ca6f81dab262a8694b738252ae',
            'input_index': 0,
            'sender_address': '1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq',
            'multisig_address': '36Q4vWxZ8co2h2UviEudacMwFadqL4TtBw',
            'color': 1,
            'amount': 1
        }
        Proposal.objects.create(source_code='fake_source_code',
                                public_key='048cfd6643a92b2681a753521c056838f3d104a91af3bf37104dba698b4c75c5025ab25d96b600fef2d105b3e005e6e4ae2c234a58f54a8683762b05fd59935052',
                                address='fake_address', multisig_address='36Q4vWxZ8co2h2UviEudacMwFadqL4TtBw')
        Keystore.objects.create(public_key='048cfd6643a92b2681a753521c056838f3d104a91af3bf37104dba698b4c75c5025ab25d96b600fef2d105b3e005e6e4ae2c234a58f54a8683762b05fd59935052',
                                private_key='6572cb0d4f04391b2fb0d23778e4d8b9eb5512759aa62f0c03ac2d1b4d5e1d05')

    def fake_open_test_state(multisig_address, option):
        return open('./app/test_files/test_state_file', option)

    @mock.patch("app.views.open", fake_open_test_state)
    def test_sign(self):
        # test gcoin multisign, the test above is a real case.
        response = self.client.post(self.url, self.sample_form)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertNotEqual(data.get('signature'), None)

    def test_invalid_form(self):
        self.sample_form['raw_tx'] = ''
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    def test_invalid_multisig_address(self):
        self.sample_form['multisig_address'] = '36Q4vWxZ8co2h2UviEudacMwFadqL4TtBs'
        response = self.client.post(self.url, self.sample_form)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['error'], 'contract not found')
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)


class MultisigAddrTest(TestCase):

    def setUp(self):
        super(MultisigAddrTest, self).setUp()
        self.url = '/multisigaddress/'
        self.sample_form = {
            'pubkey': '048cfd6643a92b2681a753521c056838f3d104a91af3bf37104dba698b4c75c5025ab25d96b600fef2d105b3e005e6e4ae2c234a58f54a8683762b05fd59935052',
            'multisig_address': '36Q4vWxZ8co2h2UviEudacMwFadqL4TtBw'
        }
        Proposal.objects.create(source_code='fake_source_code',
                                public_key='048cfd6643a92b2681a753521c056838f3d104a91af3bf37104dba698b4c75c5025ab25d96b600fef2d105b3e005e6e4ae2c234a58f54a8683762b05fd59935052',
                                address='fake_address')

    def fake_make_multisig_address_file(self):
        pass

    def fake_get_callback_url(request, multisig_address):
        callback_url = "http://172.18.250.12:7788/addressnotify/" + multisig_address
        return callback_url

    def fake_subscribe_address_notification(self, multisig_address, callback_url):
        subscription_id = "1"
        created_time = "2017-03-15"
        return subscription_id, created_time

    @mock.patch("evm_manager.deploy_contract_utils.make_multisig_address_file", fake_make_multisig_address_file)
    @mock.patch("app.views.get_callback_url", fake_get_callback_url)
    @mock.patch("gcoinapi.client.GcoinAPIClient.subscribe_address_notification", fake_subscribe_address_notification)
    def test_set_multisig_address(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    def test_invalid_form(self):
        self.sample_form['multisig_address'] = ''
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    def test_invalid_pubkey(self):
        self.sample_form[
            'pubkey'] = '048cfdd643a92b2681a753521c056838f3d104a91af3bf37104dba698b4c75c5025ab25d96b600fef2d105b3e005e6e4ae2c234a58f54a8683762b05fd59935052'
        response = self.client.post(self.url, self.sample_form)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['errors'][0]["message"], 'Cannot find proposal with this pubkey.')
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)


class AddressNotifiedCase(TestCase):
    def setUp(self):
        self.url = "/addressnotify/339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4"

        self.sample_form = {
            "tx_hash": "1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq",
            "subscription_id": '1',
            "notification_id": '2'
        }

    def fake_deploy_contracts(tx_hash):
        return True

    def fake_deploy_contracts_failed(tx_hash):
        return False

    def test_address_notified_bad_request(self):
        self.response = self.client.post(self.url, {})
        self.assertEqual(self.response.status_code, httplib.NOT_ACCEPTABLE)

    @mock.patch("evm_manager.deploy_contract_utils.deploy_contracts", fake_deploy_contracts)
    def test_address_notified(self):
        self.response = self.client.post(self.url, self.sample_form)
        self.assertEqual(self.response.status_code, httplib.OK)
