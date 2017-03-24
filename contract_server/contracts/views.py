import ast
import base58
import json
import os
import logging
import requests
from binascii import hexlify
from subprocess import PIPE, STDOUT, Popen

from django.conf import settings
from django.http import JsonResponse
from django.views.generic import View
from django.views.generic.edit import BaseFormView
from django.utils import timezone
from django.db.models import Q

from rest_framework.views import APIView, status
from rest_framework.pagination import LimitOffsetPagination

from gcoin import hash160, scriptaddr, apply_multisignatures, deserialize, mk_multisig_script
from gcoinapi.client import GcoinAPIClient
from .evm_abi_utils import (decode_evm_output, get_function_by_name, make_evm_constructor_code,
                            get_constructor_function, get_abi_list, make_evm_input_code)
from contract_server.decorators import handle_uncaught_exception
from contract_server import response_utils

from oracles.models import Oracle, SubContract, Contract
from oracles.serializers import ContractSerializer, SubContractSerializer

import contracts.serializers
from evm_manager.utils import mk_contract_address, get_nonce, wallet_address_to_evm

from contracts.serializers import CreateMultisigAddressSerializer, MultisigAddressSerializer

from .config import CONTRACT_FEE
from .exceptions import Compiled_error, Multisig_error, SubscribeAddrsssNotificationError, OracleMultisigAddressError
from .forms import (GenContractRawTxForm, GenSubContractRawTxForm,
                    ContractFunctionCallFrom, SubContractFunctionCallForm,
                    WithdrawFromContractForm)
from .models import MultisigAddress
import contracts.models

from contract_server import ERROR_CODE
from contract_server.mixins import CsrfExemptMixin

from solc import compile_source
from evm_manager import deploy_contract_utils

try:
    import http.client as httplib
except ImportError:
    import httplib


logger = logging.getLogger(__name__)
OSSclient = GcoinAPIClient(settings.OSS_API_URL)


# Create your views here.


def create_multisig_payment(from_address, to_address, color_id, amount):

    try:
        contract = Contract.objects.get(multisig_address=from_address)
    except Contract.DoesNotExist as e:
        raise e

    oracles = contract.oracles.all()
    try:
        raw_tx = OSSclient.prepare_raw_tx(from_address, to_address, amount, color_id)
    except Exception as e:
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


def get_callback_url(request, multisig_address):
    callback_url = settings.CONTRACT_SERVER_API_URL + \
        '/addressnotify/' + multisig_address
    callback_url = ''.join(callback_url.split())
    return callback_url


class WithdrawFromContract(BaseFormView, CsrfExemptMixin):
    http_method_names = ['post']
    form_class = WithdrawFromContractForm

    def form_valid(self, form):
        response = {}
        multisig_address = form.cleaned_data['multisig_address']
        user_address = form.cleaned_data['user_address']
        colors = form.cleaned_data['colors']
        amounts = form.cleaned_data['amounts']

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
        multisig_address = self.multisig_address
        to_address = form.cleaned_data['deploy_address']
        source_code = form.cleaned_data['source_code']
        data = json.loads(form.cleaned_data['data'])
        function_inputs = form.cleaned_data['function_inputs']

        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
        except Contract.DoesNotExist:
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        try:
            contract_name = data['name']
            compiled_code, interface = self._compile_code_and_interface(source_code, contract_name)
            input_value = []
            for i in function_inputs:
                input_value.append(i['value'])
            function = get_constructor_function(interface)
            evm_input_code = make_evm_constructor_code(function, input_value)
            code = json.dumps({'source_code': compiled_code + evm_input_code,
                               'multisig_addr': multisig_address, 'to_addr': to_address})
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
        output = compile_source(source_code)
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
            requests.post(url + "/multisigaddress/", data=data)

    @handle_uncaught_exception
    def form_valid(self, form):
        # required parameters
        source_code = form.cleaned_data['source_code']
        address = form.cleaned_data['address']
        m = form.cleaned_data['m']
        oracles = form.cleaned_data['oracles']
        data = json.loads(form.cleaned_data['data'])
        function_inputs = form.cleaned_data['function_inputs']

        multisig_addr = ""

        try:
            oracle_list = self._get_oracle_list(ast.literal_eval(oracles))
            conditions = data['conditions']
            multisig_addr, multisig_script, url_map_pubkeys = self._get_multisig_addr(
                oracle_list, source_code, conditions, m)
            contract_name = data['name']
            compiled_code, interface = self._compile_code_and_interface(source_code, contract_name)

            input_value = []
            if function_inputs:
                for i in function_inputs:
                    input_value.append(i['value'])
            function = get_constructor_function(interface)
            if function:
                evm_input_code = make_evm_constructor_code(function, input_value)
            else:
                evm_input_code = ''
            code = json.dumps({'source_code': compiled_code + evm_input_code,
                               'multisig_addr': multisig_addr})

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
        except Exception as e:
            response = {'status': 'Bad request. ' + str(e)}
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        try:
            callback_url = get_callback_url(self.request, multisig_addr)
            subscription_id = ""
            created_time = ""

            try:
                subscription_id, created_time = OSSclient.subscribe_address_notification(
                    multisig_addr,
                    callback_url)
            except Exception as e:
                raise SubscribeAddrsssNotificationError

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
            return JsonResponse(response, status=httplib.BAD_REQUEST)

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

    @handle_uncaught_exception
    def get(self, request, multisig_address):
        # Get contract details.
        response = {}
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
        except Contract.DoesNotExist:
            response['error'] = 'contract not found'
            return JsonResponse(response, status=httplib.NOT_FOUND)

        function_list, event_list = get_abi_list(contract.interface)
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

        function, is_constant = get_function_by_name(contract.interface, function_name)
        if not function:
            response = {'error': 'function not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        input_value = []
        if function_inputs:
            for i in function_inputs:
                input_value.append(i['value'])
        evm_input_code = make_evm_input_code(function, input_value)

        code = json.dumps({
            "function_inputs_hash": evm_input_code,
            "multisig_addr": to_address
        })

        if not is_constant:
            tx_hex = OSSclient.operate_contract_raw_tx(
                from_address, to_address, amount, color, code, CONTRACT_FEE)
            response = {'raw_tx': tx_hex}
        else:
            response = _call_constant_function(
                from_address, to_address, evm_input_code, amount, to_address)
            out = response['out']
            function_outputs = decode_evm_output(contract.interface, function_name, out)
            response['function_outputs'] = function_outputs
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

    @handle_uncaught_exception
    def get(self, request, multisig_address, deploy_address):
        # Get contract details.
        response = {}
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
            subcontract = contract.subcontract.all().filter(deploy_address=deploy_address)[0]
        except Exception as e:
            response['error'] = 'contract or subcontract not found'
            return JsonResponse(response, status=httplib.NOT_FOUND)

        function_list, event_list = get_abi_list(subcontract.interface)
        serializer = SubContractSerializer(subcontract)
        source_code = serializer.data['source_code']

        response['function_list'] = function_list
        response['events'] = event_list
        response['multisig_address'] = multisig_address
        response['deploy_address'] = deploy_address
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
        except Exception as e:
            response = {'error': 'contract or subcontract not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        function, is_constant = get_function_by_name(subcontract.interface, function_name)
        if not function:
            response = {'error': 'function not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)

        input_value = []
        for i in function_inputs:
            input_value.append(i['value'])
        evm_input_code = make_evm_input_code(function, input_value)

        code = json.dumps({
            "function_inputs_hash": evm_input_code,
            "multisig_addr": multisig_address,
            "to_addr": deploy_address
        })

        if not is_constant:
            tx_hex = OSSclient.operate_contract_raw_tx(
                from_address, multisig_address, amount, color, code, CONTRACT_FEE)
            response = {'raw_tx': tx_hex}
        else:
            response = _call_constant_function(
                from_address, multisig_address, evm_input_code, amount, deploy_address)
            out = response['out']
            function_outputs = decode_evm_output(subcontract.interface, function_name, out)
            response['function_outputs'] = function_outputs
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


class DeployContract(APIView):

    def _compile_code_and_interface(self, source_code, contract_name):
        output = compile_source(source_code)
        byte_code = output[contract_name]['bin']
        interface = output[contract_name]['abi']
        interface = json.dumps(interface)
        return byte_code, interface

    def post(self, request, multisig_address, format=None):
        serializer = contracts.serializers.ContractSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
        else:
            response = {
                'code:': ERROR_CODE['form_error'],
                'message': 'form invalid'
            }
        contract_name = data['contract_name']
        sender_address = data['sender_address']
        multisig_address = multisig_address
        source_code = data['source_code']
        try:
            compiled_code, interface = self._compile_code_and_interface(source_code, contract_name)
        except Compiled_error as e:
            response = {
                'code:': ERROR_CODE['compiled_error'],
                'message': str(e)
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)
        try:
            multisig_address_object = MultisigAddress.objects.get(address=multisig_address)
        except:
            print('multisig not found')
        nonce = get_nonce(multisig_address, sender_address)
        contract_address_byte = mk_contract_address(wallet_address_to_evm(sender_address), nonce)
        contract_address = hexlify(contract_address_byte).decode("utf-8")
        contract = contracts.models.Contract(
            source_code=source_code,
            interface=interface,
            contract_address=contract_address,
            multisig_address=multisig_address_object,
            color=1,
            amount=0)
        contract.save()
        evm_input_code = ''
        if 'function_inputs' in data:
            function_inputs = data['function_inputs']
            input_value = []
            for i in function_inputs:
                input_value.append(i['value'])
            function = get_constructor_function(interface)
            evm_input_code = make_evm_constructor_code(function, input_value)

        code = json.dumps({'source_code': compiled_code + evm_input_code,
                           'multisig_addr': multisig_address, 'to_addr': contract_address})

        tx_hex = OSSclient.deploy_contract_raw_tx(
            sender_address, multisig_address, code, CONTRACT_FEE)
        data = {'raw_tx': tx_hex, 'contract_address': contract_address}

        return response_utils.data_response(data)


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


def _call_constant_function(sender_addr, multisig_addr, byte_code, value, to_addr):
    EVM_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../../go-ethereum/build/bin/evm'
    if to_addr == multisig_addr:
        multisig_hex = base58.b58decode(multisig_addr)
        multisig_hex = hexlify(multisig_hex)
        multisig_hex = "0x" + hash160(multisig_hex)
    else:
        multisig_hex = to_addr
    sender_hex = base58.b58decode(sender_addr)
    sender_hex = hexlify(sender_hex)
    sender_hex = "0x" + hash160(sender_hex)
    contract_path = os.path.dirname(os.path.abspath(__file__)) + \
        '/../../oracle/states/' + multisig_addr
    print("Contract path: ", contract_path)

    command = '{EVM_PATH} --sender {sender_hex} --fund {value} --value {value} \
        --write {contract_path} --input {byte_code} --receiver {multisig_hex} --read {contract_path}'.format(
        EVM_PATH=EVM_PATH, sender_hex=sender_hex, value=value, contract_path=contract_path, byte_code=byte_code, multisig_hex=multisig_hex)
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    stdout, stderr = p.communicate()
    print("stdout: ", stdout)
    print("stderr: ", stderr)

    if p.returncode != 0:
        print(stderr)
        err_msg = "{}. Code: {}".format(stderr, p.returncode)
        raise Exception(err_msg)

    return {'out': stdout.decode().split()[-1]}


class MultisigAddressesView(APIView):
    """
    BITCOIN = 100000000 # 1 bitcoin == 100000000 satoshis
    CONTRACT_FEE = 1 # 1 bitcoin
    TX_FEE = 1 # 1 bitcoin, either 0 or 1 is okay.
    FEE_COLOR = 1
    CONTRACT_TX_TYPE = 5
    """
    SOLIDITY_PATH = "../solidity/solc/solc"
    serializer_class = CreateMultisigAddressSerializer
    queryset = MultisigAddress.objects.all()
    pagination_class = LimitOffsetPagination

    def _get_pubkey_from_oracle(self, url, url_map_pubkeys):
        """Get public keys from an oracle
        """
        r = requests.post(url + '/newproposals/')
        pubkey = json.loads(r.text)['public_key']
        url_map_pubkey = {
            "url": url,
            "pubkey": pubkey
        }
        logger.debug("get " + url + "'s pubkey.")
        url_map_pubkeys.append(url_map_pubkey)

    def _get_multisig_address(self, oracle_list, m):
        """Get public keys and create multisig_address
        """
        if len(oracle_list) < m:
            raise Multisig_error("The m in 'm of n' is bigger than n.")
        url_map_pubkeys = []
        pubkeys = []

        for oracle in oracle_list:
            self._get_pubkey_from_oracle(oracle['url'], url_map_pubkeys)

        for url_map_pubkey in url_map_pubkeys:
            pubkeys.append(url_map_pubkey["pubkey"])
        if len(pubkeys) != len(oracle_list):
            raise Multisig_error('there are some oracles that did not response')
        multisig_script = mk_multisig_script(pubkeys, m)
        multisig_address = scriptaddr(multisig_script)
        return multisig_address, multisig_script, url_map_pubkeys

    def _get_oracle_list(self, oracle_list):
        """Check oracle_list is matching oracles in database
        """
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

    def _save_multisig_address(self, multisig_address, url_map_pubkeys):
        """Save multisig_address at Oracle
        """
        for url_map_pubkey in url_map_pubkeys:
            url = url_map_pubkey["url"]
            data = {
                "pubkey": url_map_pubkey["pubkey"],
                "multisig_addr": multisig_address
            }
            requests.post(url + "/multisigaddress/", data=data)

    @handle_uncaught_exception
    def post(self, request):
        """Create MultisigAddress

        Args:
            m: for m-of-n multisig_address, least m oracles sign
            oracles: list of oracles

        Returns:
            multisig_address: multisig address
        """
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid(raise_exception=False):
            m = serializer.validated_data['m']
            oracles = serializer.validated_data['oracles']
        else:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(serializer.errors))

        try:
            oracle_list = self._get_oracle_list(ast.literal_eval(oracles))
            multisig_address, multisig_script, url_map_pubkeys = self._get_multisig_address(
                oracle_list, m)

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
        except Exception as e:
            response = {'status': 'Bad request. ' + str(e)}
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        try:
            callback_url = get_callback_url(self.request, multisig_address)
            subscription_id = ""
            created_time = ""

            try:
                subscription_id, created_time = OSSclient.subscribe_address_notification(
                    multisig_address,
                    callback_url)
            except Exception as e:
                raise SubscribeAddrsssNotificationError

            try:
                self._save_multisig_address(multisig_address, url_map_pubkeys)
            except Exception as e:
                raise OracleMultisigAddressError

            multisig_address_object = MultisigAddress(
                address=multisig_address,
                script=multisig_script,
                least_sign_number=m
            )

            deploy_contract_utils.make_multisig_address_file(multisig_address)

            multisig_address_object.save()
            for i in oracle_list:
                multisig_address_object.oracles.add(Oracle.objects.get(url=i["url"]))

        except Exception as e:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(e))

        data = {
            'multisig_address': multisig_address,
        }

        return response_utils.data_response(data)

    def get(self, request, format=None):
        """Get MultisigAddresses

        Args:
            limit: for pagination limit
            offset: for pagination offset

        Returns:
            multisig_addresseses: list of MultisigAddress
            query_time: query timestamp (timezome)
        """
        paginator = LimitOffsetPagination()
        multisig_addresses = MultisigAddress.objects.all()
        result_page = paginator.paginate_queryset(multisig_addresses, request)
        serializer = MultisigAddressSerializer(result_page, many=True)
        response = {'multisig_addresses': serializer.data, 'query_time': timezone.now()}

        return JsonResponse(response)


class ContractFunction(APIView):

    def post(self, request, multisig_address, contract_address, format=None):
        serializer = contracts.serializers.ContractFunctionSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
        else:
            response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'form invalid')
        sender_address = data['sender_address']
        function_name = data['function_name']
        function_inputs = ast.literal_eval(data['function_inputs'])
        amount = data['amount']
        color = data['color']

        try:
            multisig_address_object = MultisigAddress.objects.get(address=multisig_address)
        except:
            print('multisig not found')

        try:
            contract = contracts.models.Contract.objects.filter(Q(multisig_address=multisig_address_object) & Q(contract_address=contract_address))[0]
        except:
            print('contract not found')

        function, is_constant = get_function_by_name(contract.interface, function_name)
        if not function:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'function not found')

        input_value = []
        for i in function_inputs:
            input_value.append(i['value'])
        evm_input_code = make_evm_input_code(function, input_value)

        code = json.dumps({
            "function_inputs_hash": evm_input_code,
            "multisig_addr": multisig_address,
            "to_addr": contract_address
        })

        if not is_constant:
            tx_hex = OSSclient.operate_contract_raw_tx(
                sender_address, multisig_address, amount, color, code, CONTRACT_FEE)
            data = {'raw_tx': tx_hex}
        else:
            data = _call_constant_function(
                sender_address, multisig_address, evm_input_code, amount, contract_address)
            out = data['out']
            function_outputs = decode_evm_output(contract.interface, function_name, out)
            data['function_outputs'] = function_outputs
        return response_utils.data_response(data)
