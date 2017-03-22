import json
import mock
from django.test import TestCase
from events.models import Watch
from events.views import Watches, wait_for_notification
from oracles.models import Contract, SubContract

TEST_MULTISIG_ADDRESS = '3NEga9GGxi4hPYqryL1pUsDicwnDsCNYyF'
TEST_SUBSCRIPTION_ID = '90d9931e-88cd-458b-96b3-3cea31ae05e'

TEST_SUBSCRIPTION_ID_CLOSED = '90d9931e-88cd-458b-96b3-3cea31ae051'
TEST_SUBSCRIPTION_ID_EXPIRED = '90d9931e-88cd-458b-96b3-3cea31ae052'

try:
    import http.client as httplib
except ImportError:
    import httplib


class WatchCase(TestCase):

    def setUp(self):
        self.url = '/contracts/'
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            source_code = source_code_file.read().replace('\n', '')

        source_code = 'contract AttributeLookup { \
            event AttributesSet(address indexed _sender, uint _timestamp); \
            mapping(int => int) public attributeLookupMap; \
            function setAttributes(int index, int value) { \
            attributeLookupMap[index] = value; AttributesSet(msg.sender, now); } \
            function getAttributes(int index) constant returns(int) { \
            return attributeLookupMap[index]; } }'
        multisig_address = '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4'
        multisig_script = '51210224015f5f489cf8c7d558ed306daa23448a69c645aaa835981189699a143a4f5751ae'
        interface = '[{"outputs": [{"name": "", "type": "int256"}], "id": 1, \
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
            "name": "AttributesSet", "type": "event", "anonymous": false}]'

        contract = Contract.objects.create(
            source_code=source_code,
            multisig_address=multisig_address,
            multisig_script=multisig_script,
            interface=interface,
            color_id=1,
            amount=0
        )

        subscontract_source_code = 'contract AttributeLookup { \
            event AttributesSet2(address indexed _sender, uint _timestamp); \
            mapping(int => int) public attributeLookupMap; \
            function setAttributes(int index, int value) { \
            attributeLookupMap[index] = value; AttributesSet2(msg.sender, now); } \
            function getAttributes(int index) constant returns(int) { \
            return attributeLookupMap[index]; } }'

        subcontract_interface = '[{"outputs": [{"name": "", "type": "int256"}], "id": 1, \
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

        subcontract = SubContract.objects.create(
            parent_contract=contract,
            deploy_address="0000000000000000000000000000000000000157",
            source_code=subscontract_source_code,
            color_id=1,
            amount=0,
            interface=subcontract_interface)

        self.watch = Watch.objects.create(
            event_name="AttributesSet2",
            multisig_contract=contract,
            subcontract=subcontract
        )

        self.url = "/events/watches/"
        self.sample_form = {
            'multisig_address': '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4',
            'contract_address': '0000000000000000000000000000000000000157',
            'event_name': 'AttributesSet2'
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

        is_matched, contract, subcontract = Watches()._event_exists(multisig_address, contract_address, event_name)
        self.assertTrue(is_matched)
        self.assertEqual(contract.multisig_address, multisig_address)
        self.assertEqual(subcontract.deploy_address, contract_address)

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
