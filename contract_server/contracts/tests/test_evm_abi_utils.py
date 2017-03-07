from django.test import TestCase
from contracts.evm_abi_utils import (
    decode_evm_output, wrap_decoded_data,
    get_event_by_name, get_abi_list, get_constructor_function,
    get_function_by_name, make_evm_constructor_code, make_evm_input_code)


class EvmAbiUtilsTest(TestCase):
    def setUp(self):
        # mock interface
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

        self.interface_mortal = '[ \
            {"inputs": [{"name": "_address", "type": "address"}],  \
            "outputs": [], "name": "setOwner", "type": "function", \
            "payable": false, "constant": false}, \
            {"inputs": [], "outputs": [{"name": "", "type": "address"}, \
            {"name": "", "type": "int256"}], "name": "getStorage", "type": \
            "function", "payable": false, "constant": true}, \
            {"inputs": [], "outputs": [], "name": "kill", "type": \
            "function", "payable": false, "constant": false}, \
            {"inputs": [{"name": "_test_constractor", "type": "int256"}], \
            "payable": false, "type": "constructor"}]'

    def test_get_abi_list(self):
        function_list, event_list = get_abi_list(self.interface)
        event = list(filter(
            lambda item: item["name"] == "AttributesSet", event_list))[0]
        input_sender = list(filter(
            lambda item: item["name"] == "_sender", event["inputs"]))[0]
        self.assertEqual(input_sender["type"], "address")

        function = list(filter(
            lambda item: item["name"] == "setAttributes", function_list))[0]
        input_value = list(filter(
            lambda item: item["name"] == "value", function["inputs"]))[0]
        self.assertEqual(input_value["type"], "int256")

    def test_get_event_by_name(self):
        event = get_event_by_name(
            self.interface,
            'AttributesSet')

        self.assertEqual(event['anonymous'], False)
        self.assertEqual(event['name'], 'AttributesSet')

    def test_get_constructor_function(self):
        constructor = get_constructor_function(self.interface_mortal)
        self.assertEqual(constructor["inputs"][0]["name"], "_test_constractor")

    def test_get_function_by_name(self):
        function, is_constant = get_function_by_name(
            self.interface,
            'setAttributes')

        self.assertEqual(function['name'], 'setAttributes')
        self.assertEqual(is_constant, False)

    def test_wrap_decoded_data(self):
        # string
        item = {
            "type": "string",
            "value": b'hello world'
        }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], "hello world")

        # bytes
        item = {
            "type": "bytes",
            "value": b'Uf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12Uf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12'
        }
        item = wrap_decoded_data(item)
        self.assertEqual(
            item['value'], "0x5566000000000000000000000000001255660000000000000000000000000012")

        # bytes2
        item = {
            "type": "bytes2",
            "value": b'\x12\x34'
        }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], "0x1234")

        # int
        item = {
            "type": "int256",
            "value": -123
        }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], -123)

        # bool
        item = {
            "type": "bool",
            "value": True
        }
        item = wrap_decoded_data(item)
        self.assertEqual(item['value'], True)

    def test_decode_evm_output(self):
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
        out = '0x00000000000000000000000000000000000000000000000000000000000000' + \
            '200000000000000000000000000000000000000000000000000000000000000005' + \
            '68656c6c6f000000000000000000000000000000000000000000000000000000'
        function_output = decode_evm_output(interface, function_name, out)

        self.assertEqual(function_output[0]['value'], 'hello')
        self.assertEqual(function_output[0]['type'], 'string')

        # test 2: getMultiParams()
        function_name = 'getMultiParams'
        out = '0x00000000000000000000000000000000000000000000000000000000000000' + \
            'e00000000000000000000000000000000000000000000000000000000000003039' + \
            '000000000000000000000000000000000000000000000000000000000000303912' + \
            '000000000000000000000000000000000000000000000000000000000000001234' + \
            '000000000000000000000000000000000000000000000000000000000000000000' + \
            '000000000000000000000000000000000000000000000000000000012000000000' + \
            '000000000000000000000000000000000000000000000000000000010000000000' + \
            '00000000000000000000000000000000000000000000000000000568656c6c6f00' + \
            '000000000000000000000000000000000000000000000000000000000000000000' + \
            '000000000000000000000000000000000000000000000000063078313233340000' + \
            '000000000000000000000000000000000000000000000000'
        function_output = decode_evm_output(interface, function_name, out)

        test_function_output = [
            {'type': 'string', 'value': 'hello'},
            {'type': 'uint256', 'value': 12345},
            {'type': 'int256', 'value': 12345},
            {'type': 'bytes1', 'value': '0x12'},
            {'type': 'bytes2', 'value': '0x1234'},
            {'type': 'bytes', 'value': '0x307831323334'},
            {'type': 'bool', 'value': True}
        ]

        is_equal = sorted(test_function_output, key=lambda k: k['type']) == sorted(
            function_output, key=lambda k: k['type'])
        self.assertTrue(is_equal)

        # test 3: plusInt(int inputInt)
        function_name = 'plusInt'
        out = '0x00000000000000000000000000000000000000000000000000000000000030b4'
        function_output = decode_evm_output(interface, function_name, out)

        # input: {"type": "int", "value": 123}, output should be 12345 + 123 = 12468
        item = {"value": 12468, "type": "int256"}

        is_equal = function_output[0] == item
        self.assertTrue(is_equal)

        # test 4: getArray()
        function_name = 'getArray'
        out = '0x000000000000000000000000000000000000000000000000000000000000000' + \
            '0000000000000000000000000000000000000000000000000000000000000000100' + \
            '0000000000000000000000000000000000000000000000000000000000000200000' + \
            '0000000000000000000000000000000000000000000000000000000000300000000' + \
            '0000000000000000000000000000000000000000000000000000000400000000000' + \
            '0000000000000000000000000000000000000000000000000000500000000000000' + \
            '0000000000000000000000000000000000000000000000000600000000000000000' + \
            '0000000000000000000000000000000000000000000000700000000000000000000' + \
            '00000000000000000000000000000000000000000008'
        function_output = decode_evm_output(interface, function_name, out)
        # should output 12345 + 123 = 12468
        item = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]

        self.assertEqual(function_output[0]['value'], item)
        self.assertEqual(function_output[0]['type'], 'uint8[3][3]')

    def test_make_evm_constructor_code(self):
        function = {
            'inputs': [
                {'name': '_string', 'type': 'string'},
                {'name': '_bytes', 'type': 'bytes'},
                {'name': '_bytes2', 'type': 'bytes2'},
                {'name': '_bytes32', 'type': 'bytes32'},
                {'name': '_uint', 'type': 'uint256'},
                {'name': '_int', 'type': 'int256'},
                {'name': '_bool', 'type': 'bool'},
                {'name': '_address', 'type': 'address'}
            ],
            'payable': False, 'type': 'constructor'
        }
        function_inputs = [
            'hello world',
            '0x5566000000000000000000000000001255660000000000000000000000000012452544',
            '0x1134',
            '0x5566000000000000000000000000001255660000000000000000000000000012',
            12345, -123, True, '0000000000000000000000000000000000000171'
        ]

        evm_input_code = make_evm_constructor_code(function, function_inputs)
        expect_value = '' + \
            '0000000000000000000000000000000000000000000000000000000000000100' + \
            '0000000000000000000000000000000000000000000000000000000000000140' + \
            '1134000000000000000000000000000000000000000000000000000000000000' + \
            '5566000000000000000000000000001255660000000000000000000000000012' + \
            '0000000000000000000000000000000000000000000000000000000000003039' + \
            'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff85' + \
            '0000000000000000000000000000000000000000000000000000000000000001' + \
            '0000000000000000000000000000000000000000000000000000000000000171' + \
            '000000000000000000000000000000000000000000000000000000000000000b' + \
            '68656c6c6f20776f726c64000000000000000000000000000000000000000000' + \
            '0000000000000000000000000000000000000000000000000000000000000023' + \
            '5566000000000000000000000000001255660000000000000000000000000012' + \
            '4525440000000000000000000000000000000000000000000000000000000000'
        self.assertEqual(evm_input_code, expect_value)

    def test_make_evm_input_code(self):
        function = {
            'payable': False, 'outputs': [], 'type': 'function',
            'inputs': [
                {'name': '_string', 'type': 'string'},
                {'name': '_bytes', 'type': 'bytes'},
                {'name': '_bytes2', 'type': 'bytes2'},
                {'name': '_bytes32', 'type': 'bytes32'},
                {'name': '_uint', 'type': 'uint256'},
                {'name': '_int', 'type': 'int256'},
                {'name': '_bool', 'type': 'bool'},
                {'name': '_address', 'type': 'address'}
            ],
            'name': 'testEvent', 'constant': False}

        function_inputs = [
            'hello world',
            '0x5566000000000000000000000000001255660000000000000000000000000012452544',
            '0x1134',
            '0x5566000000000000000000000000001255660000000000000000000000000012',
            12345, -123, True, '0000000000000000000000000000000000000171'
        ]

        evm_input_code = make_evm_input_code(function, function_inputs)
        expect_value = '3d3456d1' + \
            '0000000000000000000000000000000000000000000000000000000000000100' + \
            '0000000000000000000000000000000000000000000000000000000000000140' + \
            '1134000000000000000000000000000000000000000000000000000000000000' + \
            '5566000000000000000000000000001255660000000000000000000000000012' + \
            '0000000000000000000000000000000000000000000000000000000000003039' + \
            'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff85' + \
            '0000000000000000000000000000000000000000000000000000000000000001' + \
            '0000000000000000000000000000000000000000000000000000000000000171' + \
            '000000000000000000000000000000000000000000000000000000000000000b' + \
            '68656c6c6f20776f726c64000000000000000000000000000000000000000000' + \
            '0000000000000000000000000000000000000000000000000000000000000023' + \
            '5566000000000000000000000000001255660000000000000000000000000012' + \
            '4525440000000000000000000000000000000000000000000000000000000000'
        self.assertEqual(evm_input_code, expect_value)
