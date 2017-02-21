from django.utils import timezone
from django.test import TestCase
from events.views import Events, Notify
from oracles.models import Contract
from events.models import Watch
from events.exceptions import *

TEST_MULTISIG_ADDRESS = '3NEga9GGxi4hPYqryL1pUsDicwnDsCNYyF'
TEST_SUBSCRIPTION_ID = '90d9931e-88cd-458b-96b3-3cea31ae05e'

TEST_SUBSCRIPTION_ID_CLOSED = '90d9931e-88cd-458b-96b3-3cea31ae051'
TEST_SUBSCRIPTION_ID_EXPIRED = '90d9931e-88cd-458b-96b3-3cea31ae052'


class NotifyTestCase(TestCase):
    def setUp(self):
        # monk contract
        source_code = ""
        multisig_address = TEST_MULTISIG_ADDRESS
        multisig_script = '514104403f136ee837c4e206dc69356bc6a4609a3cfeaf795fb7d1338f7063d9d23a3b749c0e048574dc18789f5d498e5f2827a8927cd48eb75ee1b45f88620a22649a51ae'
        interface = '[{"outputs": [{"name": "", "type": "uint256"}], "constant": true, "type": "function", "inputs": [{"name": "", "type": "address"}], "id": 1, "name": "storedUint", "payable": false}, {"outputs": [], "constant": false, "type": "function", "inputs": [{"name": "inputUint", "type": "uint256"}, {"name": "inputInt", "type": "int256"}, {"name": "inputString", "type": "string"}, {"name": "inputBytes", "type": "bytes"}], "id": 2, "name": "setValue", "payable": false}, {"id": 3, "anonymous": false, "name": "TestEvent", "type": "event", "inputs": [{"name": "_message", "indexed": false, "type": "string"}, {"name": "_my_uint", "indexed": true, "type": "uint256"}, {"name": "_my_int", "indexed": false, "type": "int256"}, {"name": "_my_address", "indexed": false, "type": "address"}, {"name": "_my_bytes", "indexed": false, "type": "bytes"}]}]'
        contract = Contract.objects.create(
            source_code=source_code,
            multisig_address=multisig_address,
            multisig_script=multisig_script,
            interface=interface,
            color_id=1,
            amount=0)
        contract.save()

        # monk watch
        subscription_id = TEST_SUBSCRIPTION_ID
        key = 'TestEvent'

        watch = Watch.objects.create(
            multisig_address=multisig_address,
            key=key,
            subscription_id=subscription_id
        )
        watch.save()

    def test_hash_key(self):
        notify = Notify()
        key = 'AttributesSet(address,uint256)'
        hashed_key = notify._hash_key(key)
        self.assertEqual(hashed_key, '70c8251d1f51f94ab26213a0dd53ead1bf32aeeb2e95bb6497d8d8bbde61b98d')

    def test_get_event_key(self):
        notify = Notify()
        multisig_address = TEST_MULTISIG_ADDRESS
        receiver_address = TEST_MULTISIG_ADDRESS
        event_name = 'TestEvent'
        key, event_args = notify._get_event_key(multisig_address, receiver_address, event_name)

        expect_key = 'TestEvent(string,uint256,int256,address,bytes)'
        self.assertEqual(key, expect_key)

        expect_event_args = [
            {'indexed': False, 'name': '_message', 'type': 'string', 'order': 0},
            {'indexed': True, 'name': '_my_uint', 'type': 'uint256', 'order': 1},
            {'indexed': False, 'name': '_my_int', 'type': 'int256', 'order': 2},
            {'indexed': False, 'name': '_my_address', 'type': 'address', 'order': 3},
            {'indexed': False, 'name': '_my_bytes', 'type': 'bytes', 'order': 4}]
        self.assertEqual(event_args, expect_event_args)

    def test_decode_event_from_logs(self):
        notify = Notify()

        logs = [
        {   "address":"1503be2df26f867d62481d93c1d55ab1ea11ad23",
            "topics":["0xf2b599259a3c14af4a4b44075e64f5d5535176716ce26402e6c5e0904ea1925d",
                "0x00000000000000000000000000000000000000000000000000000000000015be"],
            "data":"000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000015be000000000000000000000000891bc670fd33feeb556eafe7d635f298d21c153600000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000000d736d617274636f6e74726163740000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000063078313233340000000000000000000000000000000000000000000000000000",
            "transactionHash":"0000000000000000000000000000000000000000000000000000000000000000",
            "transactionIndex":0, "blockHash":"0000000000000000000000000000000000000000000000000000000000000000",
            "logIndex":0}]
        evm_address = '1503be2df26f867d62481d93c1d55ab1ea11ad23'
        key = 'TestEvent(string,uint256,int256,address,bytes)'
        event_hex = 'f2b599259a3c14af4a4b44075e64f5d5535176716ce26402e6c5e0904ea1925d'
        event_args = [
            {'type': 'string', 'name': '_message', 'order': 0, 'indexed': False},
            {'type': 'uint256', 'name': '_my_uint', 'order': 1, 'indexed': True},
            {'type': 'int256', 'name': '_my_int', 'order': 2, 'indexed': False},
            {'type': 'address', 'name': '_my_address', 'order': 3, 'indexed': False},
            {'type': 'bytes', 'name': '_my_bytes', 'order': 4, 'indexed': False}]

        event = notify._decode_event_from_logs(
            logs=logs,
            evm_address=evm_address,
            event_hex=event_hex,
            event_args=event_args,
            receiver_address=evm_address)

        expect_event = {'args': [
            {'indexed': 'False', 'name': '_message', 'type': 'string', 'value': 'smartcontract'},
            {'indexed': 'True', 'name': '_my_uint', 'type': 'uint256', 'value': 5566},
            {'indexed': 'False', 'name': '_my_int', 'type': 'int256', 'value': 5566},
            {'indexed': 'False', 'name': '_my_address', 'type': 'address', 'value': '891bc670fd33feeb556eafe7d635f298d21c1536'},
            {'indexed': 'False', 'name': '_my_bytes', 'type': 'bytes', 'value': '0x1234'}
        ]}

        self.assertEqual(event, expect_event)

    def run_get_alive_watch(self, subscription_id):
        '''For assertRaises tests
        '''
        Notify()._get_alive_watch(subscription_id)

    def test_get_alive_watch(self):
        # success
        watch = Notify()._get_alive_watch(TEST_SUBSCRIPTION_ID)
        self.assertEqual(watch.multisig_address, TEST_MULTISIG_ADDRESS)

    def test_get_alive_watch_is_closed(self):
        # mock watch
        watch = Watch.objects.create(
            multisig_address=TEST_MULTISIG_ADDRESS,
            key='TestEvent',
            subscription_id=TEST_SUBSCRIPTION_ID_CLOSED,
            is_closed=True
        )
        watch.save()

        self.assertRaises(WatchIsClosed_error, self.run_get_alive_watch, TEST_SUBSCRIPTION_ID_CLOSED)

    def test_get_alive_watch_is_expired(self):
        # mock watch
        watch = Watch.objects.create(
            multisig_address=TEST_MULTISIG_ADDRESS,
            key='TestEvent',
            subscription_id=TEST_SUBSCRIPTION_ID_EXPIRED,
            created= timezone.now() + timezone.timedelta(minutes=20)
        )
        watch.save()

        self.assertRaises(WatchIsExpired_error, self.run_get_alive_watch, TEST_SUBSCRIPTION_ID_EXPIRED)
