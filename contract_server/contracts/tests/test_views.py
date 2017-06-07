import json
import mock

from django.test import TestCase
from django.conf import settings
from contracts.exceptions import Multisig_error
from contract_server import ERROR_CODE
from contracts.models import Contract, MultisigAddress
from contracts.views import MultisigAddressesView
from oracles.models import Oracle

try:
    import http.client as httplib
except ImportError:
    import httplib


class ContractFunctionViewTest(TestCase):

    def setUp(self):
        # mock contract
        self.multisig_address = '339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4'
        self.multisig_script = '51210224015f5f489cf8c7d558ed306daa23448a69c645aaa835981189699a143a4f5751ae'
        self.multisig_address_object = MultisigAddress.objects.create(
            address=self.multisig_address,
            script=self.multisig_script,
            least_sign_number=1
        )
        self.contract_address = '5025114d3ddd53a5629739f917b5e00743cf9753'
        self.source_code = 'contract AttributeLookup { \
            event AttributesSet(address indexed _sender, uint _timestamp); \
            mapping(int => int) public attributeLookupMap; \
            function setAttributes(int index, int value) { \
            attributeLookupMap[index] = value; AttributesSet(msg.sender, now); } \
            function getAttributes(int index) constant returns(int) { \
            return attributeLookupMap[index]; } }'
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
            interface=self.interface,
            contract_address=self.contract_address,
            multisig_address=self.multisig_address_object,
            color=1,
            amount=0,
            is_deployed=True
        )

        self.url = '/smart-contract/multisig-addresses/' + self.multisig_address + '/contracts/'\
            + self.contract_address + '/function/'

        function_inputs = [
            {
                'name': 'index',
                'type': 'int',
                'value': 1
            }
        ]

        self.sample_form = {
            'sender_address': '1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq',
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

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    def test_make_non_constant_function_call_tx(self):
        self.sample_form['function_name'] = 'setAttributes'
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    @mock.patch("evm_manager.deploy_contract_utils.call_constant_function", fake_call_constant_function)
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
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    def test_post_with_non_exist_multisig_address(self):
        # non exist multisig
        url = '/smart-contract/multisig-addresses/339AXdNwaLddddPw8mkwbnJnY8CetBbUP4/\
            contracts/123/function/'
        self.sample_form['function_name'] = 'non_exist_function_name'
        response = self.client.post(url, self.sample_form)
        self.assertEqual(response.status_code, httplib.NOT_FOUND)

    @mock.patch("gcoinapi.client.GcoinAPIClient.operate_contract_raw_tx", fake_operate_contract_raw_tx)
    def test_post_with_wrong_api_version(self):
        # non exist multisig
        self.sample_form['apiVersion'] = 'wrong_api'
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.NOT_ACCEPTABLE)

    def test_miss_field_form(self):
        required_field = ['function_name', 'function_inputs', 'sender_address', 'color', 'amount']
        for field in required_field:
            miss_field_params = dict(self.sample_form)
            del miss_field_params[field]
            response = self.client.post(self.url, miss_field_params)
            self.assertEqual(response.status_code, httplib.BAD_REQUEST)


class DeployContractViewTest(TestCase):

    def setUp(self):
        self.multisig_address = "3QNNj5LFwt4fD9y8kQsMFibrELih1FCUZM"
        self.multisig_script = "51210243cdd388d600f1202ac13c70bb7bf93b80ff6a20bc39760dc389ecf8ef9f000251ae"
        MultisigAddress.objects.create(
            address=self.multisig_address,
            script=self.multisig_script,
            least_sign_number=1
        )

        self.url = '/smart-contract/multisig-addresses/' + self.multisig_address + '/contracts/'
        with open('./contracts/test_files/test_source_code', 'r') as source_code_file:
            source_code = source_code_file.read().replace('\n', '')

        self.sample_form = {
            'source_code': source_code,
            'sender_address': '1GmuEC3KHQgqtyT1oDceyxmD4RNtRsPRwq',
            "contract_name": "abc",
            "conditions": "[]"
        }

    def fake_deploy_contract_raw_tx(self, address, multisig_addr, code, CONTRACT_FEE):
        tx_hex = "010000000164ff18323fe25d3e0c70533ca111a6dd50d2a661b4b049bf6fa80d0e52441ca5020000001976a91484c5d5e87df109be8d86b76f7dc84812799cefe088acffffffff0300e1f5050000000017a914e1926963a8afee72858921b5eef3b2f1484c894c87010000000000000000000000fd39026a4d35027b22746f5f61646472223a202235303235313134643364646435336135363239373339663931376235653030373433636639373534222c20226d756c74697369675f61646472223a2022334e466a4d5a72565a646d5847487259726e705567317a63436b5550725977754c77222c2022736f757263655f636f6465223a202236303630363034303532336636313030303035373562363030313630303038313930353535303562356236306238383036313030323236303030333936303030663330303630363036303430353236303030333537633031303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303039303034363366666666666666663136383036333031373235613062313436303436353738303633333731333033633031343630363635373562363030303536356233663630303035373630353036303732353635623630343035313830383238313532363032303031393135303530363034303531383039313033393066333562336636303030353736303730363037383536356230303562363030303534383135363562363030313630303036303030383238323534303139323530353038313930353535303562353630306131363536323761376137323330353832306436626365653661326333376165616364316439363438623461633630663239396561363333353062623136656135393930393237623861316461616132336430303239227d00000000007765b07d8d03001976a91484c5d5e87df109be8d86b76f7dc84812799cefe088ac010000000000000005000000"
        return tx_hex

    def fake_compile_code_and_interface(self, source_code, contract_name):
        with open('./contracts/test_files/test_binary', 'r') as test_binary_code_file:
            test_binary_code = test_binary_code_file.read().replace('\n', '')
        with open('./contracts/test_files/test_interface', 'r') as test_abi_file:
            test_interface = test_abi_file.read().replace('\n', '')
        return test_binary_code, test_interface

    def fake_get_nonce(multisig_address, sender_address):
        return 1

    @mock.patch("gcoinapi.client.GcoinAPIClient.deploy_contract_raw_tx", fake_deploy_contract_raw_tx)
    @mock.patch("contracts.views.DeployContract._compile_code_and_interface", fake_compile_code_and_interface)
    @mock.patch("contracts.views.get_nonce", fake_get_nonce)
    def test_create_contract(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    def test_miss_field_form(self):
        required_field = ['source_code', 'sender_address', 'contract_name']
        for field in required_field:
            miss_field_params = dict(self.sample_form)
            del miss_field_params[field]
            response = self.client.post(self.url, miss_field_params)
            self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    def test_wrong_code(self):
        required_field = ['source_code', 'contract_name']
        for field in required_field:
            wrong_field_params = dict(self.sample_form)
            wrong_field_params[field] = 'wrong'
            response = self.client.post(self.url, wrong_field_params)
            self.assertNotEqual(response.status_code, httplib.OK)

    def test_wrong_apiversion(self):
        self.sample_form['apiVersion'] = 'wrong_api_version'
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.NOT_ACCEPTABLE)


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

    def fake_subscribe_address_notification(self, multisig_address, callback_url, confirmation):
        subscription_id = "1"
        created_time = "2017-03-15"
        return subscription_id, created_time

    def fake_save_multisig_address(self, multisig_addr, url_map_pubkeys):
        pass

    def fake_get_callback_url(request, multisig_address):
        callback_url = "http://172.18.250.12:7787/addressnotify/" + multisig_address
        return callback_url

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
    def test_create_contract(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)

    @mock.patch("contracts.views.MultisigAddressesView._get_multisig_address", fake_get_multisig_address_error)
    def test_create_contract_with_multisig_error(self):
        response = self.client.post(self.url, self.sample_form)
        json_data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(json_data['errors'][0]['code'], ERROR_CODE['multisig_error'])
        self.assertEqual(response.status_code, httplib.BAD_REQUEST)

    def test_get_all_multisig_address(self):
        for i in range(20):
            MultisigAddress.objects.create(
                address=str(i),
                script=str(i))

        response = self.client.get(self.url + '?limit=2&offset=0')
        json_data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(len(json_data["data"]["multisig_addresses"]), 2)


class ContractBindTest(TestCase):

    def setUp(self):
        # monk contract
        self.address = "339AXdNwaL8FJ3Pw8mkwbnJnY8CetBbUP4"
        self.script = "51210224015f5f489cf8c7d558ed306daa23448a69c645aaa835981189699a143a4f5751ae"
        self.oracles = Oracle.objects.create(url='http://52.197.157.107:5590', name='oss1')
        self.least_sign_number = 1

        self.multisig_address = MultisigAddress.objects.create(
            address=self.address,
            script=self.script,
            least_sign_number=self.least_sign_number
        )
        self.multisig_address.oracles.add(self.oracles)
        self.source_code_onlyGreeter = 'contract Greeter{ string greeting; function greeter(string _greeting) public { greeting = _greeting; } function greet() constant returns (string) { return greeting; } function setgreeter(string _greeting) public { greeting = _greeting; } }'
        self.color = 1
        self.amount = 0
        self.interface = '[{"name": "setgreeter","inputs": [{"type": "string","name": "_greeting"}]},{"name": "greet","inputs": []},{"name": "greeter","inputs": [{"type": "string","name": "_greeting"}]}]'
        self.contract_address = 'a75c04b0cf9adfdf012222347c18c9445a8fa6f2'

        self.contract_Greeter = Contract.objects.create(
            source_code=self.source_code_onlyGreeter,
            color=self.color,
            amount=self.amount,
            interface=self.interface,
            contract_address=self.contract_address,
            multisig_address=self.multisig_address,
            is_deployed=True,
        )
        self.url = '/smart-contract/multisig-addresses/' + self.address + '/bind/'

        self.sample_form = {
            'new_contract_address': 'a76c04b0cf9adfdf012222347c18c9445a8fa6f2',
            'original_contract_address': 'a75c04b0cf9adfdf012222347c18c9445a8fa6f2',
            'apiVersion': settings.API_VERSION
        }

    def test_wrong_apiversion(self):
        self.sample_form['apiVersion'] = 'wrong_api_version'
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.NOT_ACCEPTABLE)

    def test_bind(self):
        response = self.client.post(self.url, self.sample_form)
        self.assertEqual(response.status_code, httplib.OK)
        contract = Contract.objects.get(
            contract_address='a76c04b0cf9adfdf012222347c18c9445a8fa6f2',
            multisig_address=self.multisig_address
        )
        self.assertEqual(contract.interface, self.interface)
