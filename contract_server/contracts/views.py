import ast
import json
import logging
import requests

from django.conf import settings
from django.http import JsonResponse
from django.views.generic import View
from django.views.generic.edit import BaseFormView
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from gcoin import scriptaddr, apply_multisignatures, deserialize, mk_multisig_script
from rest_framework.views import APIView, status
from rest_framework.pagination import LimitOffsetPagination
from solc import compile_source


from contracts.serializers import CreateMultisigAddressSerializer, MultisigAddressSerializer, DeployContractSerializer, ContractFunctionSerializer
from contract_server import response_utils, ERROR_CODE, data_response
from contract_server.decorators import handle_uncaught_exception, handle_apiversion_apiview
from contract_server.mixins import CsrfExemptMixin, MultisigAddressCreateMixin
from evm_manager import deploy_contract_utils
from evm_manager.utils import wallet_address_to_evm
from gcoinapi.client import GcoinAPIClient
from oracles.models import Oracle

from .config import CONTRACT_FEE
from .evm_abi_utils import (decode_evm_output, get_function_by_name, make_evm_constructor_code,
                            get_constructor_function,  make_evm_input_code, get_abi_list)
from .exceptions import Multisig_error, MultisigNotFoundError, ContractNotFoundError, OssError
from .forms import BindForm
from .models import Contract, MultisigAddress

try:
    import http.client as httplib
except ImportError:
    import httplib


logger = logging.getLogger(__name__)
OSSclient = GcoinAPIClient(settings.OSS_API_URL)


# Create your views here.


def create_multisig_payment(from_address, to_address, color_id, amount):
    try:
        multisig_address = MultisigAddress.objects.get(address=from_address)
    except Exception as e:
        raise MultisigNotFoundError('MultisigNotFoundError')

    try:
        contract = Contract.objects.get(multisig_address=from_address)
    except Exception as e:
        raise ContractNotFoundError('ContractNotFoundError')

    oracles = multisig_address.oracles.all()
    try:
        raw_tx = OSSclient.prepare_raw_tx(from_address, to_address, amount, color_id)
    except Exception as e:
        raise OssError('OssError')

    # multisig sign
    # calculate counts of inputs
    tx_inputs = deserialize(raw_tx)['ins']
    for i in range(len(tx_inputs)):
        sigs = []
        for oracle in oracles:
            data = {
                'raw_tx': raw_tx,
                'multisig_address': from_address,
                'user_address': to_address,
                'color': color_id,
                'amount': amount,
                'script': contract.multisig_script,
                'input_index': i,
            }
            r = requests.post(oracle.url + '/signnew/', data=data)

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
        raise OssError('OssError')


class ContractList(View):

    def get(self, request, format=None):
        contracts = Contract.objects.all()
        data = []
        for contract in contracts:
            data.append(contract.as_dict())
        response = {'contracts': data}
        return data_response(response)


class MultisigAddressesView(APIView, MultisigAddressCreateMixin):
    """
    BITCOIN = 100000000 # 1 bitcoin == 100000000 satoshis
    CONTRACT_FEE = 1 # 1 bitcoin
    TX_FEE = 1 # 1 bitcoin, either 0 or 1 is okay.
    FEE_COLOR = 1
    CONTRACT_TX_TYPE = 5
    """
    serializer_class = CreateMultisigAddressSerializer
    queryset = MultisigAddress.objects.all()
    pagination_class = LimitOffsetPagination

    @handle_uncaught_exception
    @handle_apiversion_apiview
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
            data = serializer.validated_data
        else:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(serializer.errors))

        m = data['m']
        oracle_list = self.get_oracle_list(ast.literal_eval(data['oracles']))

        # get multisig address object
        try:
            multisig_address_object = self.get_or_create_multisig_address_object(oracle_list, m)
        except Multisig_error as e:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(e), ERROR_CODE['multisig_error'])
        except Exception as e:
            raise e
        multisig_address = multisig_address_object.address

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
        data = {
            'multisig_addresses': serializer.data,
            'query_time': timezone.now()
        }

        return response_utils.data_response(data)


class DeployContract(APIView, MultisigAddressCreateMixin):

    def _compile_code_and_interface(self, source_code, contract_name):
        output = compile_source(source_code)
        byte_code = output[contract_name]['bin']
        interface = output[contract_name]['abi']
        interface = json.dumps(interface)
        return byte_code, interface

    def _hash_op_return(self, tx_hex):
        vouts = deserialize(tx_hex)['outs']
        for vout in vouts:
            if vout['color'] == 0:
                return Contract.make_hash_op_return(vout['script'])
        raise Exception('tx_format_error')

    @handle_apiversion_apiview
    def post(self, request, format=None, *args, **kwargs):
        serializer = DeployContractSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
        else:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(serializer.errors), ERROR_CODE['invalid_form_error'])

        contract_name = data['contract_name']
        sender_address = data['sender_address']
        source_code = data['source_code']
        amount = data['amount']
        color = data['color']
        oracles = data['oracles']
        m = data['m']

        multisig_address = ''
        if 'multisig_address' in kwargs:
            multisig_address = kwargs['multisig_address']

        # Gen multisig address by oracles
        oracle_list = self.get_oracle_list(ast.literal_eval(oracles))

        # Get multisig address object
        try:
            if multisig_address:
                multisig_address_object = self.get_multisig_address_object(multisig_address)
            else:
                multisig_address_object = self.get_or_create_multisig_address_object(oracle_list, m)
        except Multisig_error as e:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(e), ERROR_CODE['multisig_error'])
        except Exception as e:
            raise e

        try:
            compiled_code, interface = self._compile_code_and_interface(source_code, contract_name)
        except Exception as e:
            response = {
                'code:': ERROR_CODE['compiled_error'],
                'message': str(e)
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        contract = Contract(
            source_code=source_code,
            interface=interface,
            state_multisig_address=multisig_address_object,
            sender_evm_address=wallet_address_to_evm(sender_address),
            color=color,
            amount=amount)

        evm_input_code = ''
        if 'function_inputs' in data:
            function_inputs = ast.literal_eval(data['function_inputs'])
            input_value = []
            for i in function_inputs:
                input_value.append(i['value'])
            function = get_constructor_function(interface)
            evm_input_code = make_evm_constructor_code(function, input_value)

        multisig_address = multisig_address_object.address
        pubkeys = []
        for oracle in oracle_list:
            pubkeys.append(self.get_pubkey_from_oracle(oracle, multisig_address))

        code = json.dumps({
            'source_code': compiled_code + evm_input_code,
            'public_keys': json.dumps(pubkeys),
        })

        try:
            tx_hex = OSSclient.operate_contract_raw_tx(
                sender_address, multisig_address, None, amount, color, code, CONTRACT_FEE)
        except Exception as e:
            print('exception...')
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, str(e))

        contract.hash_op_return = self._hash_op_return(tx_hex)
        contract.save()
        data = {
            'raw_tx': tx_hex,
            'state_multisig_address': multisig_address
        }
        return response_utils.data_response(data)


def _handle_payment_parameter_error(form):
    # the payment should at least takes the following inputs
    # from_address, to_address, amount, color
    inputs = ['sender_address', 'to_address', 'amount', 'color']
    errors = []
    for i in inputs:
        if i in form.errors:
            errors.append(form.errors[i])
        elif not form.cleaned_data.get(i):
            errors.append({i: 'require parameter {}'.format(i)})
    return {'errors': errors}


class ContractAddressList(APIView):

    def get(self, request, multisig_address, contract_address, format=None):
        data = []
        try:
            contract_address_list = Contract.objects.filter(
                multisig_address__address=multisig_address, contract_address=contract_address)
        except Contract.DoesNotExist:
            return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, 'contract_not_found_error', 'A000')
        for contract in contract_address_list:
            interface = contract.interface
            interface = json.loads(interface.replace("'", '"'))
            tx_hash_init = contract.tx_hash_init
            hash_op_return = contract.hash_op_return
            sender_evm_address = contract.sender_evm_address
            is_deployed = contract.is_deployed
            data.append({'interface': interface,
                         'tx_hash_init': tx_hash_init,
                         'hash_op_return': hash_op_return,
                         'sender_evm_address': sender_evm_address,
                         'is_deployed': is_deployed})
        return response_utils.data_response(data)


class ContractFunction(APIView):

    def _get_pubkey_from_oracles(self, oracles, multisig_address):
        """Get public keys from an oracle
        """
        pubkeys = []
        for oracle in oracles:
            url = oracle.url
            r = requests.get(url + '/api/v1/proposals/' + multisig_address)
            pubkey = json.loads(r.text)['public_key']
            logger.debug("get " + url + "'s pubkey.")
            pubkeys.append(pubkey)
        return pubkeys

    def _get_contract_multisig_address(self, pubkeys, state_multisig_address, contract_address):
        m = 0
        for i in range(len(pubkeys)):
            multisig_script = mk_multisig_script(pubkeys, i + 1)
            multisig_address = scriptaddr(multisig_script)
            if multisig_address == state_multisig_address:
                m = i + 1
                break
        if m == 0:
            raise Exception('Compute contract multisig error')
        multisig_script = mk_multisig_script(pubkeys, m, contract_address)
        multisig_address = scriptaddr(multisig_script)
        return multisig_address

    def get(self, request, multisig_address, contract_address, format=None):
        data = {}
        try:
            contract = Contract.objects.get(
                multisig_address__address=multisig_address, contract_address=contract_address, is_deployed=True)
        except Contract.DoesNotExist:
            return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, 'contract_not_found_error', 'A000')
        except Exception as e:
            return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e) + 'There are multiple deployed contract with a same contract address', )

        function_list, event_list = get_abi_list(contract.interface)
        data['function_list'] = function_list
        data['event_list'] = event_list
        return response_utils.data_response(data)

    @handle_uncaught_exception
    @handle_apiversion_apiview
    def post(self, request, state_multisig_address, contract_address, format=None):
        serializer = ContractFunctionSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
        else:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'form invalid')
        sender_address = data['sender_address']
        function_name = data['function_name']
        function_inputs = ast.literal_eval(data['function_inputs'])
        amount = data['amount']
        color = data['color']
        try:
            if 'interface' in data:
                interface = data['interface']

            else:
                try:
                    contract = Contract.objects.get(
                        contract_address=contract_address, state_multisig_address__address=state_multisig_address, is_deployed=True)
                    contract_multisig_address = contract.contract_multisig_address.address
                    interface = contract.interface
                except MultipleObjectsReturned as e:
                    return response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'found_multiple_contract', ERROR_CODE['found_multiple_contract'])
                except Exception as e:
                    raise ObjectDoesNotExist(str(e))
            function, is_constant = get_function_by_name(interface, function_name)
            if not function:
                return response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'function not found')

            input_value = []
            for i in function_inputs:
                input_value.append(i['value'])
            evm_input_code = make_evm_input_code(function, input_value)

            if 'interface' in data:
                if 'oracles' not in data:
                    return response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'Please give oracles if calling by interface.')
                oracles = []
                oracle_list = ast.literal_eval(data['oracles'])

                for oracle in oracle_list:
                    oracles.append(Oracle.objects.get(url=oracle['url']))

                pubkeys = self._get_pubkey_from_oracles(oracles, state_multisig_address)
                contract_multisig_address = self._get_contract_multisig_address(
                    pubkeys, state_multisig_address, contract_address)
            else:
                oracles = MultisigAddress.objects.get(
                    address=contract_multisig_address).oracles.all()
                pubkeys = self._get_pubkey_from_oracles(oracles, state_multisig_address)

            if is_constant:
                data = deploy_contract_utils.call_constant_function(
                    sender_address, state_multisig_address, evm_input_code, amount, contract_address)
                out = data['out']
                function_outputs = decode_evm_output(interface, function_name, out)
                data['function_outputs'] = function_outputs
            else:
                code = json.dumps({
                    "function_inputs_hash": evm_input_code,
                    'public_keys': json.dumps(pubkeys),
                })
                tx_hex = OSSclient.operate_contract_raw_tx(
                    sender_address, state_multisig_address, contract_multisig_address, amount, color, code, CONTRACT_FEE)
                data = {'raw_tx': tx_hex}
            return response_utils.data_response(data)

        except ObjectDoesNotExist as e:
            return response_utils.error_response(status.HTTP_404_NOT_FOUND, str(e))
        except Exception as e:
            print('exception... ' + str(e))
            return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


class Bind(BaseFormView, CsrfExemptMixin):

    def _get_pubkey_from_oracles(self, oracles, multisig_address):
        """Get public keys from an oracle
        """
        pubkeys = []
        for oracle in oracles:
            url = oracle.url
            r = requests.get(url + '/proposals/' + multisig_address)
            pubkey = json.loads(r.text)['public_key']
            logger.debug("get " + url + "'s pubkey.")
            pubkeys.append(pubkey)
        return pubkeys

    def _get_contract_multisig_address(self, pubkeys, state_multisig_address, contract_address):
        m = 0
        for i in range(len(pubkeys)):
            multisig_script = mk_multisig_script(pubkeys, i + 1)
            multisig_address = scriptaddr(multisig_script)
            if multisig_address == state_multisig_address:
                m = i + 1
                break
        if m == 0:
            raise Exception('Compute contract multisig error')
        multisig_script = mk_multisig_script(pubkeys, m, contract_address)
        multisig_address = scriptaddr(multisig_script)
        return multisig_address, multisig_script, m

    @handle_uncaught_exception
    @handle_apiversion_apiview
    def post(self, request, multisig_address):

        form = BindForm(request.POST)
        if form.is_valid():
            new_contract_address = form.cleaned_data['new_contract_address']
            original_contract_address = form.cleaned_data['original_contract_address']
            try:
                original_contract = Contract.objects.get(
                    contract_address=original_contract_address, state_multisig_address__address=multisig_address, is_deployed=True)
                oracles = original_contract.state_multisig_address.oracles.all()
                pubkeys = self._get_pubkey_from_oracles(oracles, multisig_address)
                contract_multisig_address, contract_multisig_script, m = self._get_contract_multisig_address(
                    pubkeys, original_contract.state_multisig_address.address, original_contract_address)

                contract_multisig_address_object = MultisigAddress.objects.create(
                    address=contract_multisig_address, script=contract_multisig_script, least_sign_number=m)

                for oracle in oracles:
                    contract_multisig_address_object.oracles.add(oracle)

                contract_multisig_address_object.save()
            except Exception as e:
                print('except: ' + str(e))
                # Todo
                return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, 'contract_not_found_error', 'A000')

            try:
                new_contract, created = Contract.objects.get_or_create(
                    source_code=original_contract.source_code,
                    color=original_contract.color,
                    amount=original_contract.amount,
                    interface=original_contract.interface,
                    contract_address=new_contract_address,
                    state_multisig_address=original_contract.state_multisig_address,
                    contract_multisig_address=contract_multisig_address_object,
                    is_deployed=True,
                    hash_op_return=original_contract.hash_op_return
                )

                if created:
                    data = {"is_success": True}
                    return response_utils.data_response(data)
                else:
                    # TODO
                    return response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'contract address already exist')
            except Exception as e:
                return response_utils.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))

        else:
            return response_utils.error_response(status.HTTP_400_BAD_REQUEST, 'invalid_form_error', 'Z002')
