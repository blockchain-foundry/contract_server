import json
import mock
from django.test import TestCase
from events.models import Watch
from events.views import Watches, wait_for_notification
from contracts.models import MultisigAddress, Contract

try:
    import http.client as httplib
except ImportError:
    import httplib


class WatchCase(TestCase):

    def fake_subscribe_address_notification(self, multisig_address, callback_url):
        subscription_id = '1'
        created_time = '2017-03-15'
        return subscription_id, created_time

    @mock.patch("gcoinapi.client.GcoinAPIClient.subscribe_address_notification", fake_subscribe_address_notification)
    def setUp(self):
        self.url = '/contracts/'
        multisig_address = '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4'
        multisig_script = '51210224015f5f489cf8c7d558ed306daa23448a69c645aaa835981189699a143a4f5751ae'
        multisig_address_object = MultisigAddress.objects.create(
            address=multisig_address,
            script=multisig_script)

        contract_source_code = 'contract AttributeLookup { \
            event AttributesSet2(address indexed _sender, uint _timestamp); \
            mapping(int => int) public attributeLookupMap; \
            function setAttributes(int index, int value) { \
            attributeLookupMap[index] = value; AttributesSet2(msg.sender, now); } \
            function getAttributes(int index) constant returns(int) { \
            return attributeLookupMap[index]; } }'

        contract_interface = '[{"outputs": [{"name": "", "type": "int256"}], "id": 1, \
            "inputs": [{"name": "index", "type": "int256"}], \
            "constant": true, "payable": false, "name": "getAttributes", \
            "type": "function"}, {"outputs": [], "id": 2, \
            "inputs": [{"name": "index", "type": "int256"}, \
            {"name": "value", "type": "int256"}], \
            "constant": false, "payable": false, "name": "setAttributes", \
            "type": "function"}, {"outputs": [{"name": "", "type": "int256"}], \
            "id": 3, "inputs": [{"name": "", "type": "int256"}], "constant": true, \
            "payable": false, "name": "attributeLookupMap", "type": "function"}, \
            {"id": 4, "inputs": [{"indexed": true, "name": "_sender", "type": "address"}, \
            {"indexed": false, "name": "_timestamp", "type": "uint256"}], \
            "name": "AttributesSet2", "type": "event", "anonymous": false}]'

        contract = Contract.objects.create(
            state_multisig_address=multisig_address_object,
            contract_address="0000000000000000000000000000000000000157",
            source_code=contract_source_code,
            color=1,
            amount=0,
            interface=contract_interface)

        self.watch = Watch.objects.create(
            event_name="AttributesSet2",
            contract=contract
        )

        self.url = "/events/watches/"
        self.sample_form = {
            'multisig_address': '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4',
            'contract_address': '0000000000000000000000000000000000000157',
            'event_name': 'AttributesSet2'
        }

        self.sample_form_condition = {
            'multisig_address': '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4',
            'contract_address': '0000000000000000000000000000000000000157',
            'event_name': 'AttributesSet2',
            'conditions': str(
                [{"value": "hello world", "type": "string", "name": "event_string"}]
            )
        }

    def fake_wait_for_notification(watch_id):
        args = [{"value": "hello world", "type": "string", "name": "event_string", "indexed": True}]
        event = {
            "args": args,
            "name": "AttributesSet2"
        }
        return event

    def test_wait_for_notification_success(self):
        watch_id = self.watch.id

        args = [{"value": "hello world", "type": "string", "name": "event_string", "indexed": True}]
        self.watch.args = json.dumps(args)
        self.watch.save()
        event = wait_for_notification(watch_id)

        self.assertEqual(event["name"], "AttributesSet2")
        self.assertEqual(event["args"][0]["value"], "hello world")

    def test_event_exists_success(self):
        multisig_address = "339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4"
        contract_address = "0000000000000000000000000000000000000157"
        event_name = "AttributesSet2"

        is_matched, contract = Watches()._event_exists(multisig_address, contract_address, event_name)
        self.assertTrue(is_matched)
        self.assertEqual(contract.state_multisig_address.address, multisig_address)
        self.assertEqual(contract.contract_address, contract_address)

    @mock.patch("events.views.wait_for_notification", fake_wait_for_notification)
    def test_process_watch_event_successs(self):
        multisig_address = "339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4"
        event_name = "AttributesSet2"
        contract_address = "0000000000000000000000000000000000000157"

        self.response = Watches()._process_watch_event(
            multisig_address=multisig_address,
            event_name=event_name,
            contract_address=contract_address
        )
        self.assertEqual(self.response.status_code, httplib.OK)

    def test_watch_event_bad_request(self):
        self.response = self.client.post(self.url, {})
        self.assertEqual(self.response.status_code, httplib.BAD_REQUEST)

    @mock.patch("events.views.wait_for_notification", fake_wait_for_notification)
    def test_watch_event_success(self):
        self.response = self.client.post(self.url, self.sample_form)
        self.assertEqual(self.response.status_code, httplib.OK)

    @mock.patch("events.views.wait_for_notification", fake_wait_for_notification)
    def test_watch_event_success_condition(self):
        self.response = self.client.post(self.url, self.sample_form_condition)
        self.assertEqual(self.response.status_code, httplib.OK)
