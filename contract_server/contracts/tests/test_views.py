import json
from django.test import TestCase
from oracles.models import Contract
from contracts.views import ContractFunc


class ContractFuncTest(TestCase):

    def setUp(self):
        # monk contract
        source_code = 'contract AttributeLookup { event AttributesSet(address indexed _sender, uint _timestamp); mapping(int => int) public attributeLookupMap; function setAttributes(int index, int value) { attributeLookupMap[index] = value; AttributesSet(msg.sender, now); } function getAttributes(int index) constant returns(int) { return attributeLookupMap[index]; } }'
        multisig_addr = '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4'
        multisig_script = '51210224015f5f489cf8c7d558ed306daa23448a69c645aaa835981189699a143a4f5751ae'
        interface = '[{"outputs": [{"name": "", "type": "int256"}], "id": 1, "inputs": [{"name": "index", "type": "int256"}], "constant": true, "payable": false, "name": "getAttributes", "type": "function"}, {"outputs": [], "id": 2, "inputs": [{"name": "index", "type": "int256"}, {"name": "value", "type": "int256"}], "constant": false, "payable": false, "name": "setAttributes", "type": "function"}, {"outputs": [{"name": "", "type": "int256"}], "id": 3, "inputs": [{"name": "", "type": "int256"}], "constant": true, "payable": false, "name": "attributeLookupMap", "type": "function"}, {"id": 4, "inputs": [{"indexed": true, "name": "_sender", "type": "address"}, {"indexed": false, "name": "_timestamp", "type": "uint256"}], "name": "AttributesSet", "type": "event", "anonymous": false}]'

        self.contract = Contract(
            source_code=source_code,
            multisig_address=multisig_addr,
            multisig_script=multisig_script,
            interface=interface,
            color_id=1,
            amount=0)

    def test_get_abi_list(self):
        contract_func = ContractFunc()
        function_list, event_list = contract_func._get_abi_list(self.contract.interface)

        self.assertEqual(function_list[0]['name'], 'getAttributes')
        self.assertEqual(event_list[0]['name'], 'AttributesSet')
