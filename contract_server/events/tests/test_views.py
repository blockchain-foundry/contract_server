from django.test import TestCase
from events.views import Events, Notify
from oracles.models import Contract
from events.models import Watch

TEST_MULTISIG_ADDRESS = '34EbmGsm5cBedTDQ7c9q3EmM8miVpURwrb'
TEST_SUBSCRIPTION_ID = '597caf7b-7d60-4d3f-9dd4-a4ccb9b36ea8'

class NotifyTestCase(TestCase):
    def setUp(self):
        # monk contract
        source_code = "contract TestGcoin { event TestEvent( string _message, uint indexed _my_uint, int _my_int , uint _timestamp, address _my_address); uint password = 12345; string message = 'hello'; mapping(address => uint) public storedUint; function setUint(uint inputUint, int inputInt, string inputString) { storedUint[msg.sender] = inputUint; password = inputUint; TestEvent( inputString, inputUint, inputInt, now, msg.sender); } }"
        multisig_address = TEST_MULTISIG_ADDRESS
        multisig_script = '514104e989178111484245d79e7bf65a97dd4d0b626586946016ae2080b5cdb8d214f7f4fa18651f22dde3c33469e7ea83b07fbf6eb1cd78c7d6f9a73d6ee6e5a8572551ae'
        interface = '[{"constant": true, "type": "function", "name": "storedUint", "outputs": [{"type": "uint256", "name": ""}], "payable": false, "id": 1, "inputs": [{"type": "address", "name": ""}]}, {"constant": false, "type": "function", "name": "setUint", "outputs": [], "payable": false, "id": 2, "inputs": [{"type": "uint256", "name": "inputUint"}, {"type": "int256", "name": "inputInt"}, {"type": "string", "name": "inputString"}]}, {"type": "event", "id": 3, "inputs": [{"type": "string", "indexed": false, "name": "_message"}, {"type": "uint256", "indexed": true, "name": "_my_uint"}, {"type": "int256", "indexed": false, "name": "_my_int"}, {"type": "uint256", "indexed": false, "name": "_timestamp"}, {"type": "address", "indexed": false, "name": "_my_address"}], "name": "TestEvent", "anonymous": false}]'

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

    def test__get_event_key(self):
        notify = Notify()
        multisig_address = TEST_MULTISIG_ADDRESS
        event_name = 'TestEvent'
        key, event_args = notify._get_event_key(multisig_address, event_name)

        expect_key = 'TestEvent(string,uint256,int256,uint256,address)'
        self.assertEqual(key, expect_key)

        expect_event_args = [{'indexed': False, 'name': '_message', 'type': 'string', 'order': 0}, {'indexed': True, 'name': '_my_uint', 'type': 'uint256', 'order': 1}, {'indexed': False, 'name': '_my_int', 'type': 'int256', 'order': 2}, {'indexed': False, 'name': '_timestamp', 'type': 'uint256', 'order': 3}, {'indexed': False, 'name': '_my_address', 'type': 'address', 'order': 4}]
        self.assertEqual(event_args, expect_event_args)

    def test_get_event_from_logs(self):
        notify = Notify()

        logs = [{'blockHash': '0000000000000000000000000000000000000000000000000000000000000000', 'logIndex': 0, 'address': 'e7cb54645a4cc9856319e68e278c6ce967d06fc3', 'transactionIndex': 0, 'topics': ['0xfee4a3829113d3807b9bb7f2b510ff21dd8734905679bb13a1d2f5b5633cb79e', '0x00000000000000000000000000000000000000000000000000000000000015be'], 'data': '000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000015be000000000000000000000000000000000000000000000000000000005885f1cd000000000000000000000000c38303f940a55b93aac72f3af15442c1a9f834e7000000000000000000000000000000000000000000000000000000000000000a68656c6c6f776f726c6400000000000000000000000000000000000000000000', 'transactionHash': '0000000000000000000000000000000000000000000000000000000000000000'}]
        evm_address = 'e7cb54645a4cc9856319e68e278c6ce967d06fc3'
        event_hex = 'fee4a3829113d3807b9bb7f2b510ff21dd8734905679bb13a1d2f5b5633cb79e'
        event_args = [{'type': 'string', 'name': '_message', 'order': 0, 'indexed': False}, {'type': 'uint256', 'name': '_my_uint', 'order': 1, 'indexed': True}, {'type': 'int256', 'name': '_my_int', 'order': 2, 'indexed': False}, {'type': 'uint256', 'name': '_timestamp', 'order': 3, 'indexed': False}, {'type': 'address', 'name': '_my_address', 'order': 4, 'indexed': False}]

        event = notify._get_event_from_logs(
            logs=logs,
            evm_address=evm_address,
            event_hex=event_hex,
            event_args=event_args)

        expect_event = {'args': [{'type': 'string', 'name': '_message', 'value': 'helloworld', 'indexed': 'False'}, {'type': 'uint256', 'name': '_my_uint', 'value': 5566, 'indexed': 'True'}, {'type': 'int256', 'name': '_my_int', 'value': 5566, 'indexed': 'False'}, {'type': 'uint256', 'name': '_timestamp', 'value': 1485173197, 'indexed': 'False'}, {'type': 'address', 'name': '_my_address', 'value': 'c38303f940a55b93aac72f3af15442c1a9f834e7', 'indexed': 'False'}]}
        self.assertEqual(event, expect_event)

