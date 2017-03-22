import json
import mock

from django.test import TestCase

from contracts.exceptions import Multisig_error
from contract_server import ERROR_CODE
from oracles.models import Contract, Oracle
from contracts.views import MultisigAddressesView
from contracts.models import MultisigAddress


try:
    import http.client as httplib
except ImportError:
    import httplib


class ContractFuncTest(TestCase):

    def setUp(self):
        # mock contract
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
        self.url = '/smart-contract/contracts/' + self.multisig_address + '/'

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
        return 'fake tx hex'

    def fake_call_constant_function(sender_addr, multisig_addr, byte_code, value, to_addr):
        return {
            'out': 'fake contstant call result',
        }

    def fake_decode_evm_output(interface, function_name, out):
        return {
            'function_outputs': 'fake funciton output'
        }

    def test_get_abi_list(self):
        response = self.client.get(self.url)
        json_data = json.loads(response.content.decode('utf-8'))
        function_list = json_data['function_list']
        event_list = json_data['events']

        self.assertEqual(function_list[0]['name'], 'getAttributes')
        self.assertEqual(event_list[0]['name'], 'AttributesSet')

    def test_get_contract_detail(self):
        response = self.client.get(self.url)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['multisig_address'], self.multisig_address)
        self.assertEqual(json_data['source_code'], self.source_code)
        self.assertEqual(response.status_code, httplib.OK)

    def test_get_with_non_exist_multisig_address(self):
        self.url = '/smart-contract/contracts/339AXdNwaLddddPw8mkwbnJnY8CetBbUP4/'
        response = self.client.get(self.url)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['error'], 'contract not found')
        self.assertEqual(response.status_code, httplib.NOT_FOUND)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    def test_make_non_constant_function_call_tx(self):
        self.sample_form['function_name'] = 'setAttributes'
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    @mock.patch("contracts.views._call_constant_function", fake_call_constant_function)
    @mock.patch("contracts.views.decode_evm_output", fake_decode_evm_output)
    def test_make_constant_function_call_tx(self):
        # Need more tests in detail.
        self.sample_form['function_name'] = 'getAttributes'
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
        self.url = '/smart-contract/contracts/339AXdNwaLddddPw8mkwbnJnY8CetBbUP4/'
        self.sample_form['function_name'] = 'non_exist_function_name'
        response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['error'], 'contract not found')
        self.assertEqual(response.status_code, httplib.NOT_FOUND)


class ContractViewTest(TestCase):

    def setUp(self):
        self.url = '/smart-contract/contracts/'
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            source_code = source_code_file.read().replace('\n', '')
        Oracle.objects.create(url='http://52.197.157.107:5590', name='oss1')
        self.sample_form = {
            'source_code': source_code,
            'address': '1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq',
            'm': 1,
            'oracles': "[{'url': 'http://52.197.157.107:5590', 'name': 'oss1'}]",
            'data': '{"name": "abc", "conditions": "[]"}'
        }

    def fake_get_multisig_addr(self, oracle_list, source_code, conditions, m):
        multisig_addr = "3QNNj5LFwt4fD9y8kQsMFibrELih1FCUZM"
        multisig_script = "51210243cdd388d600f1202ac13c70bb7bf93b80ff6a20bc39760dc389ecf8ef9f000251ae"
        url_map_pubkeys = [
            {'pubkey': '03f485a69657f9fb4536e9c60c412c23f84ac861d2cbf60304c8a8f7fa9e769c50', 'url': 'http://52.197.157.107:5590'}]
        return multisig_addr, multisig_script, url_map_pubkeys

    def fake_get_multisig_addr_error(self, oracle_list, source_code, conditions, m):
        raise Multisig_error("fake_get_multisig_addr_error")

    def fake_deploy_contract_raw_tx(self, address, multisig_addr, code, CONTRACT_FEE):
        tx_hex = "fake tx hex"
        return tx_hex

    def fake_save_multisig_addr(self, multisig_addr, url_map_pubkeys):
        pass

    def fake_compile_code_and_interface(self, source_code, contract_name):
        with open('./contracts/test_files/test_binary', 'r') as test_binary_code_file:
            test_binary_code = test_binary_code_file.read().replace('\n', '')
        with open('./contracts/test_files/test_interface', 'r') as test_abi_file:
            test_interface = test_abi_file.read().replace('\n', '')
        return test_binary_code, test_interface

    def fake_subscribe_address_notification(self, multisig_address, callback_url):
        subscription_id = "1"
        created_time = "2017-03-15"
        return subscription_id, created_time

    def fake_get_callback_url(request, multisig_address):
        callback_url = "http://172.18.250.12:7787/addressnotify/" + multisig_address
        return callback_url

    @mock.patch("contracts.views.Contracts._get_multisig_addr", fake_get_multisig_addr)
    @mock.patch("gcoinapi.client.GcoinAPIClient.deploy_contract_raw_tx", fake_deploy_contract_raw_tx)
    @mock.patch("contracts.views.Contracts._save_multisig_addr", fake_save_multisig_addr)
    @mock.patch("contracts.views.Contracts._compile_code_and_interface", fake_compile_code_and_interface)
    @mock.patch("gcoinapi.client.GcoinAPIClient.subscribe_address_notification", fake_subscribe_address_notification)
    @mock.patch("contracts.views.get_callback_url", fake_get_callback_url)
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

        self.url = "/smart-contract/withdraw/"

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


class MultisigAddressesViewTest(TestCase):

    def setUp(self):
        self.url = '/smart-contract/multisig-addresses/'
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            source_code = source_code_file.read().replace('\n', '')
        Oracle.objects.create(url='http://52.197.157.107:5590', name='oss1')
        self.sample_form = {
            'source_code': source_code,
            'address': '1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq',
            'm': 1,
            'oracles': "[{'url': 'http://52.197.157.107:5590', 'name': 'oss1'}]",
            'data': '{"name": "abc", "conditions": "[]"}'
        }

    def fake_get_multisig_address(self, oracle_list, m):
        multisig_addr = "3QNNj5LFwt4fD9y8kQsMFibrELih1FCUZM"
        multisig_script = "51210243cdd388d600f1202ac13c70bb7bf93b80ff6a20bc39760dc389ecf8ef9f000251ae"
        url_map_pubkeys = [
            {'pubkey': '03f485a69657f9fb4536e9c60c412c23f84ac861d2cbf60304c8a8f7fa9e769c50', 'url': 'http://52.197.157.107:5590'}]
        return multisig_addr, multisig_script, url_map_pubkeys

    def fake_get_multisig_address_error(self, oracle_list, m):
        raise Multisig_error("fake_get_multisig_addr_error")

    def fake_deploy_contract_raw_tx(self, address, multisig_addr, code, CONTRACT_FEE):
        tx_hex = "fake tx hex"
        return tx_hex

    def fake_compile_code_and_interface(self, source_code, contract_name):
        with open('./contracts/test_files/test_binary', 'r') as test_binary_code_file:
            test_binary_code = test_binary_code_file.read().replace('\n', '')
        with open('./contracts/test_files/test_interface', 'r') as test_abi_file:
            test_interface = test_abi_file.read().replace('\n', '')
        return test_binary_code, test_interface

    def fake_subscribe_address_notification(self, multisig_address, callback_url):
        subscription_id = "1"
        created_time = "2017-03-15"
        return subscription_id, created_time

    def fake_save_multisig_address(self, multisig_addr, url_map_pubkeys):
        pass

    def fake_get_callback_url(request, multisig_address):
        callback_url = "http://172.18.250.12:7787/addressnotify/" + multisig_address
        return callback_url

    def fake_make_multisig_address_file(self):
        pass

    def test_get_oracle_list(self):
        oracle_list = [
            {"url": "http://52.197.157.107:5590", "name": "oss1"}
        ]

        checked_oracle_list = MultisigAddressesView()._get_oracle_list(oracle_list)
        self.assertEqual(checked_oracle_list[0]["name"], "oss1")

    @mock.patch("contracts.views.MultisigAddressesView._get_multisig_address", fake_get_multisig_address)
    @mock.patch("gcoinapi.client.GcoinAPIClient.deploy_contract_raw_tx", fake_deploy_contract_raw_tx)
    @mock.patch("contracts.views.MultisigAddressesView._save_multisig_address", fake_save_multisig_address)
    @mock.patch("gcoinapi.client.GcoinAPIClient.subscribe_address_notification", fake_subscribe_address_notification)
    @mock.patch("contracts.views.get_callback_url", fake_get_callback_url)
    @mock.patch("evm_manager.deploy_contract_utils.make_multisig_address_file", fake_make_multisig_address_file)
    def test_create_contract(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    @mock.patch("contracts.views.MultisigAddressesView._get_multisig_address", fake_get_multisig_address_error)
    def test_create_contract_with_multisig_error(self):
        response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['code'], ERROR_CODE['multisig_error'])
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    def test_get_all_multisig_address(self):
        for i in range(20):
            MultisigAddress.objects.create(
                address=str(i),
                script=str(i))

        response = self.client.get(self.url + '?limit=2&offset=0')
        json_data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(len(json_data["multisig_addresses"]), 2)
