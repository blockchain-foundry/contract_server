import ast
import json
import logging
from binascii import hexlify
from subprocess import PIPE, STDOUT, CalledProcessError, Popen, check_call
from threading import Thread

import base58
import requests
import sha3  # keccak_256
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.views.generic.edit import BaseFormView

from gcoinapi.client import GcoinAPIClient
from eth_abi.abi import *
from contract_server.decorators import handle_uncaught_exception
from contract_server.utils import *
from gcoin import *
from oracles.models import Oracle, Contract, SubContract
from oracles.serializers import *

from .config import *
from .forms import GenContractRawTxForm, GenSubContractRawTxForm, ContractFunctionCallFrom, SubContractFunctionCallForm, WithdrawFromContractForm

from contract_server import ERROR_CODE
from contract_server.mixins import CsrfExemptMixin
from .exceptions import *

from solc import compile_source

try:
    import http.client as httplib
except ImportError:
    import httplib


logger = logging.getLogger(__name__)
OSSclient = GcoinAPIClient(settings.OSS_API_URL)


# Create your views here.

def wallet_address_to_evm(address):
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)

    return address


def create_multisig_payment(from_address, to_address, color_id, amount):

    try:
        contract = Contract.objects.get(multisig_address=from_address)
    except Contract.DoesNotExist as e:
        raise e

    oracles = contract.oracles.all()
    try:
        raw_tx = OSSclient.prepare_raw_tx(from_address, to_address, amount, color_id)
    except:
        return {'error': 'prepare multisig payment failed'}

    # multisig sign
    # calculate counts of inputs
    tx_inputs = deserialize(raw_tx)['ins']
    for i in range(len(tx_inputs)):
        sigs = []
        for oracle in oracles:
            data = {
                'tx': raw_tx,
                'multisig_address': from_address,
                'user_address': to_address,
                'color_id': color_id,
                'amount': amount,
                'script': contract.multisig_script,
                'input_index': i,
            }
            r = requests.post(oracle.url + '/sign/', data=data)

            signature = r.json().get('signature')
            print('Get ' + oracle.url + '\'s signature.')
            if signature is not None:
                # sign success, update raw_tx
                sigs.append(signature)
        raw_tx = apply_multisignatures(raw_tx, i, contract.multisig_script,
                                       sigs[:contract.least_sign_number])

    # send
    try:
        tx_id = OSSclient.send_tx(raw_tx)
        return {'tx_id': tx_id}
    except Exception as e:
        raise e


class WithdrawFromContract(BaseFormView, CsrfExemptMixin):
    http_method_names = ['post']
    form_class = WithdrawFromContractForm

    def form_valid(self, form):
        response = {}
        multisig_address = form.cleaned_data['multisig_address']
        user_address = form.cleaned_data['user_address']
        colors = form.cleaned_data['colors']
        amounts = form.cleaned_data['amounts']

        user_evm_address = wallet_address_to_evm(user_address)

        # create payment for each color and store the results
        # in tx list or error list
        txs = []
        errors = []
        for color_id, amount in zip(colors, amounts):
            color_id = int(color_id)
            amount = int(amount)
            if amount == 0:  # it will always show color = 0 at evm
                continue

            try:
                r = create_multisig_payment(multisig_address, user_address, color_id, amount)
            except Exception as e:
                response['error'] = str(e)
                return JsonResponse(response, status=httplib.BAD_REQUEST)
            tx_id = r.get('tx_id')

            if tx_id is None:
                errors.append({color_id: r})
                continue
            txs.append(tx_id)

        response['txs'] = txs
        response['error'] = errors

        if txs:
            return JsonResponse(response, status=httplib.OK)
        return JsonResponse(response, status=httplib.BAD_REQUEST)

    def form_invalid(self, form):
        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class SubContracts(BaseFormView, CsrfExemptMixin):

    http_method_names = ['post']
    form_class = GenSubContractRawTxForm

    def _compile_code_and_interface(self, source_code, contract_name):        
        output = compile_source(source_code)
        byte_code = output[contract_name]['bin']
        interface = output[contract_name]['abi'] 
        interface = json.dumps(interface)
        return byte_code, interface

    def post(self, request):
        return super().post(request)

    @handle_uncaught_exception
    def form_valid(self, form):
        '''
        This function will make a tx (user transfer money to multisig address)
        of contract type and op_return=function_inputs and function_id
        The oracle monitor will notice the created tx
        and then tunrs it to evn state

        inputs: from_address, to_address, amount, color, function_inputs, function_id
        `function_inputs` is a list
        '''
        multisig_address = form.cleaned_data['multisig_address']
        from_address = form.cleaned_data['from_address']
        to_address = form.cleaned_data['deploy_address']
        source_code = form.cleaned_data['source_code']
        data = json.loads(form.cleaned_data['data'])

        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
        except Contract.DoesNotExist:
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)
        
        try:
            
            contract_name = data['name']
            compiled_code, interface = self._compile_code_and_interface(source_code, contract_name)
            code = json.dumps({'source_code': compiled_code, 'multisig_addr': multisig_address, 'to_addr': to_address})
            subcontract = SubContract(
                parent_contract=contract,
                deploy_address=to_address,
                source_code=source_code,
                color_id=1,
                amount=0,
                interface=interface)
            subcontract.save()

        except Compiled_error as e:
            response = {
                'code:': ERROR_CODE['compiled_error'],
                'message': str(e)
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        tx_hex = OSSclient.deploy_contract_raw_tx(
            from_address, multisig_address, code, CONTRACT_FEE)
        response = {'raw_tx': tx_hex}

        return JsonResponse(response)

    @handle_uncaught_exception
    def form_invalid(self, form):
        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class Contracts(BaseFormView, CsrfExemptMixin):
    '''
    BITCOIN = 100000000 # 1 bitcoin == 100000000 satoshis
    CONTRACT_FEE = 1 # 1 bitcoin
    TX_FEE = 1 # 1 bitcoin, either 0 or 1 is okay.
    FEE_COLOR = 1
    CONTRACT_TX_TYPE = 5
    '''
    SOLIDITY_PATH = "../solidity/solc/solc"
    http_method_names = ['post']
    form_class = GenContractRawTxForm

    def _get_pubkey_from_oracle(self, url, source_code, conditions, url_map_pubkeys):
        '''
            get public keys from an oracle
        '''
        data = {
            'source_code': source_code,
            'conditions': str(conditions)
        }
        r = requests.post(url + '/proposals/', data=data)
        pubkey = json.loads(r.text)['public_key']
        url_map_pubkey = {
            "url": url,
            "pubkey": pubkey
        }
        print("get " + url + "'s pubkey.")
        url_map_pubkeys.append(url_map_pubkey)

    def _get_multisig_addr(self, oracle_list, source_code, conditions, m):
        """
            get public keys and create multisig_address
        """
        if len(oracle_list) < m:
            raise Multisig_error("The m in 'm of n' is bigger than n.")
        url_map_pubkeys = []
        pubkeys = []
        threads = []

        for oracle in oracle_list:
            self._get_pubkey_from_oracle(oracle['url'], source_code, conditions, url_map_pubkeys)

        for url_map_pubkey in url_map_pubkeys:
            pubkeys.append(url_map_pubkey["pubkey"])
        if len(pubkeys) != len(oracle_list):
            raise Multisig_error('there are some oracles that did not response')
        multisig_script = mk_multisig_script(pubkeys, m)
        multisig_addr = scriptaddr(multisig_script)
        return multisig_addr, multisig_script, url_map_pubkeys

    def _get_oracle_list(self, oracle_list):
        if len(oracle_list) == 0:
            oracle_list = []
            for i in Oracle.objects.all():
                oracle_list.append(
                    {
                        'name': i.name,
                        'url': i.url
                    }
                )
        return oracle_list

    def _compile_code_and_interface(self, source_code, contract_name):
        try:
            output = compile_source(source_code)
        except Exception as e:
            print(str(e))
        byte_code = output[contract_name]['bin']
        interface = output[contract_name]['abi']
        interface = json.dumps(interface)
        return byte_code, interface

    def _save_multisig_addr(self, multisig_addr, url_map_pubkeys):
        for url_map_pubkey in url_map_pubkeys:
            url = url_map_pubkey["url"]
            data = {
                "pubkey": url_map_pubkey["pubkey"],
                "multisig_addr": multisig_addr
            }
            r = requests.post(url + "/multisigaddress/", data=data)

    @handle_uncaught_exception
    def form_valid(self, form):
        # required parameters
        source_code = form.cleaned_data['source_code']
        address = form.cleaned_data['address']
        m = form.cleaned_data['m']
        oracles = form.cleaned_data['oracles']
        data = json.loads(form.cleaned_data['data'])
        try:
            oracle_list = self._get_oracle_list(ast.literal_eval(oracles))

            conditions = data['conditions']
            multisig_addr, multisig_script, url_map_pubkeys = self._get_multisig_addr(
                oracle_list, source_code, conditions, m)

            contract_name = data['name']
            compiled_code, interface = self._compile_code_and_interface(source_code, contract_name)
            code = json.dumps({'source_code': compiled_code, 'multisig_addr': multisig_addr})

        except Compiled_error as e:
            response = {
                'code:': ERROR_CODE['compiled_error'],
                'message': str(e)
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)
        except Multisig_error as e:
            response = {
                'code': ERROR_CODE['multisig_error'],
                'message': str(e)
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        try:
            tx_hex = OSSclient.deploy_contract_raw_tx(address, multisig_addr, code, CONTRACT_FEE)

            self._save_multisig_addr(multisig_addr, url_map_pubkeys)
            contract = Contract(
                source_code=source_code,
                multisig_address=multisig_addr,
                multisig_script=multisig_script,
                interface=interface,
                color_id=1,
                amount=0,
                least_sign_number=m
            )

            contract.save()
            for i in oracle_list:
                contract.oracles.add(Oracle.objects.get(url=i["url"]))

            data = {
                "multisig_addr": multisig_addr,
                "compiled_code": compiled_code
            }
        except Exception as e:
            response = {'status': 'Bad request. ' + str(e)}
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)

        response = {
            'multisig_address': multisig_addr,
            'oracles': oracle_list,
            'tx': tx_hex
        }
        return JsonResponse(response, status=httplib.OK)

    @handle_uncaught_exception
    def form_invalid(self, form):
        response = {
            'error': form.errors
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class ContractFunc(BaseFormView, CsrfExemptMixin):

    CONTRACTS_PATH = '../oracle/'  # collect contracts genertaed by evm under oracle directory
    HARDCODE_ADDRESS = '0x3510ce1b33081dc972ae0854f44728a74da9f291'
    EVM_COMMAND_PATH = '../go-ethereum/build/bin/evm'

    http_method_names = ['get', 'post']
    form_class = ContractFunctionCallFrom

    def _get_abi_list(self, interface):
        if not interface:
            return [], []

        # The outermost quote must be ', otherwise json.loads will fail
        interface = json.loads(interface.replace("'", '"'))
        function_list = []
        event_list = []
        for i in interface:
            if i['type'] == 'function':
                function_list.append({
                    'name': i['name'],
                    'inputs': i['inputs']
                })
            elif i['type'] == 'event':
                event_list.append({
                    'name': i['name'],
                    'inputs': i['inputs']
                })
        return function_list, event_list

    def _get_event_by_name(self, interface, event_name):
        '''
        interface is string of a list of dictionary containing id, name, type, inputs and outputs
        '''
        if not interface:
            return {}

        interface = json.loads(interface.replace("'", '"'))
        for i in interface:
            name = i.get('name')
            if name == event_name and i['type'] == 'event':
                return i
        return {}

    def _get_function_by_name(self, interface, function_name):
        '''
        interface is string of a list of dictionary containing id, name, type, inputs and outputs
        '''
        if not interface:
            return {}

        interface = json.loads(interface.replace("'", '"'))
        for i in interface:
            name = i.get('name')
            if name == function_name and i['type'] == 'function':
                return i
        return {}

    def _evm_input_code(self, function, args):
        types = [self._process_type(i['type']) for i in function['inputs']]
        func = function['name'] + '(' + ','.join(types) + ')'
        func = func.encode()
        k = sha3.keccak_256()
        k.update(func)
        evm_func = k.hexdigest()[:8]

        # evm_args = bytes_evm_args.hex() in python 3.5
        bytes_evm_args = encode_abi(types, args)
        evm_args = ''.join(format(x, '02x') for x in bytes_evm_args)
        return evm_func + evm_args

    def _process_type(self, typ):
        if(len(typ) == 3 and typ[:3] == "int"):
            return "int256"
        if(len(typ) == 4 and typ[:4] == "uint"):
            return "uint256"
        if(len(typ) > 4 and typ[:4] == "int["):
            return "int256[" + typ[4:]
        if(len(typ) > 5 and typ[:5] == "uint["):
            return "uint256[" + typ[5:]
        return typ

    @handle_uncaught_exception
    def get(self, request, multisig_address):
        # Get contract details.
        response = {}
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
        except Contract.DoesNotExist:
            response['error'] = 'contract not found'
            return JsonResponse(response, status=httplib.NOT_FOUND)

        function_list, event_list = self._get_abi_list(contract.interface)
        serializer = ContractSerializer(contract)
        addrs = serializer.data['multisig_address']
        source_code = serializer.data['source_code']

        response['function_list'] = function_list
        response['events'] = event_list
        response['multisig_address'] = addrs
        response['source_code'] = source_code

        return JsonResponse(response, status=httplib.OK)

    def post(self, request, multisig_address):
        self.multisig_address = multisig_address
        return super().post(request, multisig_address)

    @handle_uncaught_exception
    def form_valid(self, form):
        '''
        This function will make a tx (user transfer money to multisig address)
        of contract type and op_return=function_inputs and function_id
        The oracle monitor will notice the created tx
        and then tunrs it to evn state

        inputs: from_address, to_address, amount, color, function_inputs, function_id
        `function_inputs` is a list
        '''
        from_address = form.cleaned_data['from_address']
        to_address = self.multisig_address
        amount = form.cleaned_data['amount']
        color = form.cleaned_data['color']
        function_name = form.cleaned_data['function_name']
        function_inputs = form.cleaned_data['function_inputs']

        try:
            contract = Contract.objects.get(multisig_address=to_address)
        except Contract.DoesNotExist:
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        function = self._get_function_by_name(contract.interface, function_name)
        if not function:
            response = {'error': 'function not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        input_value = []
        for i in function_inputs:
            input_value.append(i['value'])
        evm_input_code = self._evm_input_code(function, input_value)

        code = json.dumps({
            "function_inputs_hash": evm_input_code,
            "multisig_addr": to_address
        })
        tx_hex = OSSclient.operate_contract_raw_tx(
            from_address, to_address, amount, color, code, CONTRACT_FEE)
        response = {'raw_tx': tx_hex}

        return JsonResponse(response)

    @handle_uncaught_exception
    def form_invalid(self, form):
        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class SubContractFunc(BaseFormView, CsrfExemptMixin):

    CONTRACTS_PATH = '../oracle/'  # collect contracts genertaed by evm under oracle directory
    HARDCODE_ADDRESS = '0x3510ce1b33081dc972ae0854f44728a74da9f291'
    EVM_COMMAND_PATH = '../go-ethereum/build/bin/evm'

    http_method_names = ['get', 'post']
    form_class = SubContractFunctionCallForm

    def _get_abi_list(self, interface):
        if not interface:
            return [], []

        # The outermost quote must be ', otherwise json.loads will fail
        interface = json.loads(interface.replace("'", '"'))
        function_list = []
        event_list = []
        for i in interface:
            if i['type'] == 'function':
                function_list.append({
                    'name': i['name'],
                    'inputs': i['inputs']
                })
            elif i['type'] == 'event':
                event_list.append({
                    'name': i['name'],
                    'inputs': i['inputs']
                })
        return function_list, event_list

    def _get_event_by_name(self, interface, event_name):
        '''
        interface is string of a list of dictionary containing id, name, type, inputs and outputs
        '''
        if not interface:
            return {}

        interface = json.loads(interface.replace("'", '"'))
        for i in interface:
            name = i.get('name')
            if name == event_name and i['type'] == 'event':
                return i
        return {}

    def _get_function_by_name(self, interface, function_name):
        '''
        interface is string of a list of dictionary containing id, name, type, inputs and outputs
        '''
        if not interface:
            return {}

        interface = json.loads(interface.replace("'", '"'))
        for i in interface:
            name = i.get('name')
            if name == function_name and i['type'] == 'function':
                return i
        return {}

    def _evm_input_code(self, function, args):
        types = [self._process_type(i['type']) for i in function['inputs']]
        func = function['name'] + '(' + ','.join(types) + ')'
        func = func.encode()
        k = sha3.keccak_256()
        k.update(func)
        evm_func = k.hexdigest()[:8]

        # evm_args = bytes_evm_args.hex() in python 3.5
        bytes_evm_args = encode_abi(types, args)
        evm_args = ''.join(format(x, '02x') for x in bytes_evm_args)
        return evm_func + evm_args

    def _process_type(self, typ):
        if(len(typ) == 3 and typ[:3] == "int"):
            return "int256"
        if(len(typ) == 4 and typ[:4] == "uint"):
            return "uint256"
        if(len(typ) > 4 and typ[:4] == "int["):
            return "int256[" + typ[4:]
        if(len(typ) > 5 and typ[:5] == "uint["):
            return "uint256[" + typ[5:]
        return typ

    @handle_uncaught_exception
    def get(self, request, multisig_address, deploy_address):
        # Get contract details.
        response = {}
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
            subcontract = contract.subcontract.all().filter(deploy_address=deploy_address)[0]
        except Contract.DoesNotExist:
            response['error'] = 'contract or subcontract not found'
            return JsonResponse(response, status=httplib.NOT_FOUND)
        function_list, event_list = self._get_abi_list(subcontract.interface)

        serializer = SubContractSerializer(subcontract)

        addrs = serializer.data['deploy_address']
        source_code = serializer.data['source_code']

        response['function_list'] = function_list
        response['events'] = event_list
        response['deploy_address'] = addrs
        response['source_code'] = source_code

        return JsonResponse(response, status=httplib.OK)

    def post(self, request, multisig_address, deploy_address):
        self.multisig_address = multisig_address
        self.deploy_address = deploy_address
        return super().post(request, multisig_address, deploy_address)

    @handle_uncaught_exception
    def form_valid(self, form):
        '''
        This function will make a tx (user transfer money to multisig address)
        of contract type and op_return=function_inputs and function_id
        The oracle monitor will notice the created tx
        and then tunrs it to evn state

        inputs: from_address, to_address, amount, color, function_inputs, function_id
        `function_inputs` is a list
        '''
        from_address = form.cleaned_data['from_address']
        deploy_address = self.deploy_address
        multisig_address = self.multisig_address
        amount = form.cleaned_data['amount']
        color = form.cleaned_data['color']
        function_name = form.cleaned_data['function_name']
        function_inputs = form.cleaned_data['function_inputs']

        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
            subcontract = contract.subcontract.all().filter(deploy_address=deploy_address)[0]
        except Contract.DoesNotExist:
            response = {'error': 'contract or subcontract not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        function = self._get_function_by_name(subcontract.interface, function_name)
        if not function:
            response = {'error': 'function not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        input_value = []
        for i in function_inputs:
            input_value.append(i['value'])
        evm_input_code = self._evm_input_code(function, input_value)

        code = json.dumps({
            "function_inputs_hash": evm_input_code,
            "multisig_addr": multisig_address,
            "to_addr": deploy_address
        })
        tx_hex = OSSclient.operate_contract_raw_tx(
            from_address, multisig_address, amount, color, code, CONTRACT_FEE)
        response = {'raw_tx': tx_hex}

        return JsonResponse(response)

    @handle_uncaught_exception
    def form_invalid(self, form):
        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class ContractList(View):

    def get(self, request, format=None):
        contracts = Contract.objects.all()
        serializer = ContractSerializer(contracts, many=True)
        response = {'contracts': serializer.data}
        return JsonResponse(response)


def _handle_payment_parameter_error(form):
    # the payment should at least takes the following inputs
    # from_address, to_address, amount, color
    inputs = ['from_address', 'to_address', 'amount', 'color']
    errors = []
    for i in inputs:
        if i in form.errors:
            errors.append(form.errors[i])
        elif not form.cleaned_data.get(i):
            errors.append({i: 'require parameter {}'.format(i)})
    return {'errors': errors}
