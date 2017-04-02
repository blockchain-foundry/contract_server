import sha3
from django.test import TestCase
from django.utils import timezone

from events.models import Watch
from contracts.models import MultisigAddress, Contract
from contracts.evm_abi_utils import get_event_by_name


EVENT_NAME = "AttributesSet2"


class ModelWatchTestCase(TestCase):

    def setUp(self):
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
            multisig_address=multisig_address_object,
            contract_address="0000000000000000000000000000000000000157",
            source_code=contract_source_code,
            color=1,
            amount=0,
            interface=contract_interface,
        )

        Watch.objects.create(
            event_name=EVENT_NAME,
            contract=contract,
            conditions='[ {"name": "_sender", "type:": "address", "value": "4f8c35f1ca068863047fcdb4a3c4f82f565aadb8"}]'
        )

    def test_hashed_event_name(self):
        watch = Watch.objects.get(event_name=EVENT_NAME)

        k = sha3.keccak_256()
        k.update(watch.event_name.encode())
        self.assertEqual(watch.hashed_event_name, k.hexdigest())

    def test_is_expired(self):
        watch = Watch.objects.get(event_name=EVENT_NAME)
        self.assertEqual(watch.is_expired, False)

        watch.created = watch.created + timezone.timedelta(minutes=20)
        self.assertEqual(watch.is_expired, True)

    def test_is_triggered(self):
        watch = Watch.objects.get(event_name=EVENT_NAME)
        self.assertFalse(watch.is_triggered)

        watch.args = "..."
        watch.save()
        self.assertTrue(watch.is_triggered)

    def test_interface(self):
        watch = Watch.objects.get(event_name=EVENT_NAME)
        event = get_event_by_name(watch.contract.interface, "AttributesSet2")
        self.assertEqual(event["type"], "event")

    def test_contract_address(self):
        watch = Watch.objects.get(event_name=EVENT_NAME)
        self.assertEqual(watch.contract.contract_address, "0000000000000000000000000000000000000157")

    def test_conditions_list(self):
        watch = Watch.objects.get(event_name=EVENT_NAME)
        self.assertEqual(watch.conditions_list[0]["value"], "4f8c35f1ca068863047fcdb4a3c4f82f565aadb8")
