import json
import mock

from django.conf import settings
from django.test import TestCase

from contracts.exceptions import *
from contracts.views import ContractFunc
from contract_server import ERROR_CODE
from oracles.models import Contract, Oracle

try:
    import http.client as httplib
except ImportError:
    import httplib


class ContractFuncTest(TestCase):

    def setUp(self):
        # monk contract
        self.source_code = 'contract AttributeLookup { \
            event AttributesSet(address indexed _sender, uint _timestamp); \
            mapping(int => int) public attributeLookupMap; \
            function setAttributes(int index, int value) { \
            attributeLookupMap[index] = value; AttributesSet(msg.sender, now); } \
            function getAttributes(int index) constant returns(int) { \
            return attributeLookupMap[index]; } }'
        self.multisig_address = '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4'
        self.multisig_script = '51210224015f5f489cf8c7d558ed306daa23448a69c645aaa835981189699a143a4f5751ae'
        self.interface = '[{"outputs": [{"name": "", "type": "int256"}], "id": 1, \
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

        self.contract = Contract.objects.create(
            source_code=self.source_code,
            multisig_address=self.multisig_address,
            multisig_script=self.multisig_script,
            interface=self.interface,
            color_id=1,
            amount=0)
        self.url = '/contracts/' + self.multisig_address + '/'

        function_inputs = [
            {
                'name': 'index',
                'type': 'int',
                'value': 1
            }
        ]

        self.sample_form = {
            'from_address': '1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq',
            'amount': 1,
            'color': 1,
            'function_name': 'getAttributes',
            'function_inputs': str(function_inputs)
        }

    def fake_operate_contract_raw_tx(self, from_address, to_address, amount, color_id, compiled_code, contract_fee):
        return "fake tx hex"

    def test_get_abi_list(self):
        contract_func = ContractFunc()
        function_list, event_list = contract_func._get_abi_list(self.contract.interface)

        self.assertEqual(function_list[0]['name'], 'getAttributes')
        self.assertEqual(event_list[0]['name'], 'AttributesSet')

    def test_get_contract_detail(self):
        response = self.client.get(self.url)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['multisig_address'], self.multisig_address)
        self.assertEqual(json_data['source_code'], self.source_code)
        self.assertEqual(response.status_code, httplib.OK)

    def test_get_with_non_exist_multisig_address(self):
        self.url = '/contracts/339AXdNwaLddddPw8mkwbnJnY8CetBbUP4/'
        response = self.client.get(self.url)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['error'], 'contract not found')
        self.assertEqual(response.status_code, httplib.NOT_FOUND)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    def test_make_function_call_tx(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    def test_make_non_exist_function_call_tx(self):
        self.sample_form['function_name'] = 'non_exist_function_name'
        response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['error'], 'function not found')
        self.assertEqual(response.status_code, httplib.NOT_FOUND)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    def test_post_with_non_exist_multisig_address(self):
        # non exist multisig
        self.url = '/contracts/339AXdNwaLddddPw8mkwbnJnY8CetBbUP4/'
        self.sample_form['function_name'] = 'non_exist_function_name'
        response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['error'], 'contract not found')
        self.assertEqual(response.status_code, httplib.NOT_FOUND)


class ContractViewTest(TestCase):

    def setUp(self):
        self.url = "/contracts/"
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            source_code = source_code_file.read().replace('\n', '')
        Oracle.objects.create(url='http://52.197.157.107:5590', name='oss1')
        self.sample_form = {
            "source_code": source_code,
            "address": "1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq",
            "m": 1,
            "oracles": "[{'url': 'http://52.197.157.107:5590', 'name': 'oss1'}]"
        }

    def fake_get_multisig_addr(self, oracle_list, source_code, m):
        multisig_addr = "3QNNj5LFwt4fD9y8kQsMFibrELih1FCUZM"
        multisig_script = "51210243cdd388d600f1202ac13c70bb7bf93b80ff6a20bc39760dc389ecf8ef9f000251ae"
        url_map_pubkeys = [
            {'pubkey': '03f485a69657f9fb4536e9c60c412c23f84ac861d2cbf60304c8a8f7fa9e769c50', 'url': 'http://52.197.157.107:5590'}]
        return multisig_addr, multisig_script, url_map_pubkeys

    def fake_get_multisig_addr_error(self, oracle_list, source_code, m):
        raise Multisig_error("fake_get_multisig_addr_error")

    def fake_deploy_contract_raw_tx(self, address, multisig_addr, code, CONTRACT_FEE):
        tx_hex = "fake tx hex"
        return tx_hex

    def fake_save_multisig_addr(self, multisig_addr, url_map_pubkeys):
        pass

    @mock.patch("contracts.views.Contracts._get_multisig_addr", fake_get_multisig_addr)
    @mock.patch("gcoinapi.client.GcoinAPIClient.deploy_contract_raw_tx", fake_deploy_contract_raw_tx)
    @mock.patch("contracts.views.Contracts._save_multisig_addr", fake_save_multisig_addr)
    def test_create_contract(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    @mock.patch("contracts.views.Contracts._get_multisig_addr", fake_get_multisig_addr_error)
    def test_create_contract_with_multisig_error(self):
        response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['code'], ERROR_CODE['multisig_error'])
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)


class WithdrawFromContractTest(TestCase):

    def setUp(self):
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            self.source_code = source_code_file.read().replace('\n', '')
        self.multisig_address = '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4'
        self.multisig_script = '51210224015f5f489cf8c7d558ed306daa23448a69c645aaa835981189699a143a4f5751ae'
        self.interface = '[{"outputs": [{"name": "", "type": "int256"}], "id": 1, \
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

        self.contract = Contract.objects.create(
            source_code=self.source_code,
            multisig_address=self.multisig_address,
            multisig_script=self.multisig_script,
            interface=self.interface,
            color_id=1,
            amount=0)

        self.url = "/withdraw/"

        self.sample_form = {
            "multisig_address": "339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4",
            "user_address": "1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq",
            "colors": '[1]',
            "amounts": '[1]'
        }

    def fake_create_multisig_payment(from_address, to_address, color_id, amount):
        return {"tx_id": "fake successful tx hex"}

    def fake_create_multisig_payment_error(from_address, to_address, color_id, amount):
        raise Exception("invalid raw tx")

    @mock.patch("contracts.views.create_multisig_payment", fake_create_multisig_payment)
    def test_withdraw_from_contract(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    @mock.patch("contracts.views.create_multisig_payment", fake_create_multisig_payment_error)
    def test_withdraw_from_contract_create_multisif_payment_error(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    def test_withdraw_from_contract_wrong_multisig_address(self):
        # wrong multisig address
        self.sample_form['multisig_address'] = '339AXdNwadddd3Pw8mkwbnJnY8CetBbUP4'
        response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['error'], 'Contract matching query does not exist.')
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    def test_get_event_by_name(self):
        contract_func = ContractFunc()
        TEST_EVENT_NAME = 'AttributesSet'
        event = contract_func._get_event_by_name(self.contract.interface, TEST_EVENT_NAME)

        self.assertEqual(event['anonymous'], False)
        self.assertEqual(event['name'], TEST_EVENT_NAME)

    def test_decode_evm_output(self):
        contract_func = ContractFunc()

        '''
        pragma solidity ^0.4.7;
        contract TestGcoin {
            string myString = 'hello';
            uint myUint = 12345;
            int myInt = 12345;
            bytes1 myBytes1 = 0x12;
            bytes2 myBytes2 = 0x1234;
            bytes myBytes = '0x1234';
            bool myBool = true;


            function plusInt(int inputInt) constant returns (int) {
                return myInt + inputInt;
            }

            function getSingleParam() constant returns (string) {
                return myString;
            }

            function getMultiParams() constant returns (string, uint, int, bytes1, bytes2, bytes, bool) {
                return (myString, myUint, myInt, myBytes1, myBytes2, myBytes, myBool);
            }


            function getArray() constant returns (uint8[3][3])
            {
                uint8[3][3] memory array;
                uint8 count = 0;
                for(uint8 x = 0; x < 3; x++)
                {
                	for(uint8 y = 0; y < 3; y++)
                	{
                		array[x][y] = count;
                        count = count + 1;
                	}
                }
              	return array;
            }
        }
        '''

        interface = '[{"payable": false, "name": "getMultiParams", "outputs": [{"name": "", "type": "string"}, {"name": "", "type": "uint256"}, {"name": "", "type": "int256"}, {"name": "", "type": "bytes1"}, {"name": "", "type": "bytes2"}, {"name": "", "type": "bytes"}, {"name": "", "type": "bool"}], "inputs": [], "type": "function", "id": 1, "constant": true}, {"payable": false, "name": "plusInt", "outputs": [{"name": "", "type": "int256"}], "inputs": [{"name": "inputInt", "type": "int256"}], "type": "function", "id": 2, "constant": true}, {"payable": false, "name": "getArray", "outputs": [{"name": "", "type": "uint8[3][3]"}], "inputs": [], "type": "function", "id": 3, "constant": true}, {"payable": false, "name": "getSingleParam", "outputs": [{"name": "", "type": "string"}], "inputs": [], "type": "function", "id": 4, "constant": true}]'

        # test 1: getSingleParam()
        function_name = 'getSingleParam'
        out = '0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000568656c6c6f000000000000000000000000000000000000000000000000000000'
        function_output = contract_func._decode_evm_output(interface, function_name, out)

        self.assertEqual(function_output[0]['value'], 'hello')
        self.assertEqual(function_output[0]['type'], 'string')

        # test 2: getMultiParams()
        function_name = 'getMultiParams'
        out = '0x00000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000000000000000000000000000000000000000303900000000000000000000000000000000000000000000000000000000000030391200000000000000000000000000000000000000000000000000000000000000123400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001200000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000568656c6c6f00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000063078313233340000000000000000000000000000000000000000000000000000'
        function_output = contract_func._decode_evm_output(interface, function_name, out)

        test_function_output = [
            {'type': 'string', 'value': 'hello'}, {'type': 'uint256', 'value': 12345},
            {'type': 'int256', 'value': 12345},
            {'type': 'bytes1', 'value': '\x12'}, {'type': 'bytes2', 'value': '\x124'},
            {'type': 'bytes', 'value': '0x1234'}, {'type': 'bool', 'value': True}
        ]

        is_equal = sorted(test_function_output, key=lambda k: k['type']) == sorted(function_output, key=lambda k: k['type'])
        self.assertTrue(is_equal)

        # test 3: plusInt(int inputInt)
        function_name = 'plusInt'
        out = '0x00000000000000000000000000000000000000000000000000000000000030b4'
        function_output = contract_func._decode_evm_output(interface, function_name, out)

        # input: {"type": "int", "value": 123}, output should be 12345 + 123 = 12468
        item = {"value": 12468, "type": "int256"}

        is_equal = function_output[0] == item
        self.assertTrue(is_equal)

        # test 4: getArray()
        function_name = 'getArray'
        out = '0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000005000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000070000000000000000000000000000000000000000000000000000000000000008'
        function_output = contract_func._decode_evm_output(interface, function_name, out)
        # should output 12345 + 123 = 12468
        item = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]

        self.assertEqual(function_output[0]['value'], item)
        self.assertEqual(function_output[0]['type'], 'uint8[3][3]')
