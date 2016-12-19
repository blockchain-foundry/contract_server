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
from rest_framework.views import APIView, status

from gcoinapi.client import GcoinAPIClient
from contract_server.decorators import handle_uncaught_exception
from contract_server.utils import *
from gcoin import *
from oracles.models import Oracle, Contract
from oracles.serializers import *

from .config import *
from .forms import ContractFunctionPostForm, WithdrawForm

from contract_server import ERROR_CODE
from .exceptions import *

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

    contract = Contract.objects.get(multisig_address=from_address)
    oracles = contract.oracles.all()
    try:
        raw_tx = OSSclient.prepare_raw_tx(from_address, to_address, amount, color_id)
    except:
        return {'error': 'prepare multisig payment failed'}

    # multisig sign
    for oracle in oracles:
        data = {
            'transaction': raw_tx,
            'multisig_address': from_address,
            'user_address': to_address,
            'color_id': color_id,
            'amount': amount,
            'script': contract.multisig_script
        }
        r = requests.post(oracle.url+'/sign/', data=data)

        signature = r.json().get('signature')
        if signature is not None:
            # sign success, update raw_tx
            raw_tx = signature

    # send
    try:
        return {'tx_id' :OSSclient.send_tx(raw_tx)}
    except: 
        return {'error': 'sign multisig payment failed'}

@csrf_exempt
def withdraw_from_contract(request):
    json_data = json.loads(request.body.decode('utf8'))

    if json_data is not None:
        multisig_address = json_data['multisig_address']
        user_address = json_data['user_address']
        colors = json_data['colors']
        amounts = json_data['amounts']


        user_evm_address = wallet_address_to_evm(user_address)

        # create payment for each color and store the results
        # in tx list or error list
        txs = []
        errors = []
        for color_id, amount in zip(colors, amounts):
            color_id = int(color_id)
            amount = int(amount)
            if amount == 0: # it will always show color = 0 at evm
                continue

            r = create_multisig_payment(multisig_address, user_address, color_id, amount)
            tx_id = r.get('tx_id')
            if tx_id is None:
                errors.append({color_id: r})
                continue
            txs.append(tx_id)

        response = {'txs': txs, 'errors': errors}
        if txs:
            return JsonResponse(response)
        return JsonResponse(response, status=httplib.BAD_REQUEST)

    response = {'error': form.errors}
    return JsonResponse(response, status=httplib.BAD_REQUEST)

class Contracts(APIView):
    '''
    BITCOIN = 100000000 # 1 bitcoin == 100000000 satoshis
    CONTRACT_FEE = 1 # 1 bitcoin
    TX_FEE = 1 # 1 bitcoin, either 0 or 1 is okay.
    FEE_COLOR = 1
    CONTRACT_TX_TYPE = 5
    '''
    SOLIDITY_PATH = "../solidity/solc/solc"

    @handle_uncaught_exception
    def get(self, request):
        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)
        addrs = json_data['multisig_address']
        try:
            contract = Contract.objects.get(multisig_address=json_data['multisig_address'])
            serializer = ContractSerializer(contract)
            addrs = serializer.data['multisig_address']
            source_code = serializer.data['source_code']
            response = {'multisig_address':addrs,'source_code':source_code, 'intereface':[]}
            return JsonResponse(response)
        except:
            response = {'status': 'contract not found.'}
            return JsonResponse(
                    json_data['multisig_address'],
                    status=status.HTTP_404_NOT_FOUND
            )


    def _get_pubkey_from_oracle(self, url, source_code, url_map_pubkeys):
        '''
            get public keys from an oracle
        '''

        data = {
            'source_code': source_code
        }
        r = requests.post(url + '/proposals/', data=json.dumps(data))
        pubkey = json.loads(r.text)['public_key']
        url_map_pubkey = {
            "url": url,
            "pubkey": pubkey
        }
        url_map_pubkeys.append(url_map_pubkey)

    def _get_multisig_addr(self, oracle_list, source_code, m):
        """
            get public keys and create multisig_address
        """
        
        if len(oracle_list) < m:
            raise Multisig_error("The m in 'm of n' is bigger than n.")
        url_map_pubkeys = []
        pubkeys = []
        threads = []
        for oracle in oracle_list:
            t = Thread(target=self._get_pubkey_from_oracle,
                       args=(oracle['url'], source_code, url_map_pubkeys)
                   )
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        for url_map_pubkey in url_map_pubkeys:
            pubkeys.append(url_map_pubkey["pubkey"])
        if len(pubkeys) != len(oracle_list):
            raise Multisig_error('there are some oracles that did not response')
        multisig_script = mk_multisig_script(pubkeys, m)
        # must do in python2
        cmd = 'python2 scriptaddr.py ' + multisig_script
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = p.communicate()
        multisig_addr = stdout.decode("utf-8").strip()
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

    def _compile_code_and_interface(self, source_code):        
        command = [self.SOLIDITY_PATH, "--abi", "--bin"]
        try:
            p = Popen(command, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        except Exception as e:
            print(e)
        r = str(p.communicate(input=bytes(source_code, "utf8"))[0], "utf8")
        r = r.strip()
        if p.returncode != 0:
            raise Compiled_error(str(r))
        
        str1 = r.split('Binary:')
        str2 = str1[1].split('\n')
        compiled_code_in_hex = str2[1]
        abi = str2[3]
        abi =json.loads(abi)
        interface = []
        ids = 1
        for func in abi:
            try:
                func["id"] = ids
                interface.append(func)
                ids = ids + 1
            except:
                pass
        interface = json.dumps(interface)
        return compiled_code_in_hex, interface

    def _save_multisig_addr(self, multisig_addr, url_map_pubkeys):
        for url_map_pubkey in url_map_pubkeys:
            url =  url_map_pubkey["url"]
            data = {
                "pubkey": url_map_pubkey["pubkey"],
                "multisig_addr": multisig_addr
            }
            r = requests.post(url+"/multisigaddress/", data=json.dumps(data))

    @handle_uncaught_exception
    def post(self, request):
        # required parameters
        try:
            body_unicode = request.body.decode('utf-8')
            json_data = json.loads(body_unicode)
            source_code = str(json_data['source_code'])
        except:
            response = { 
                'status': 'Wrong inputs.',
                'message': 'no source code or in wrong data type'}
            return JsonResponse(response, status=status.HTTP_406_NOT_ACCEPTABLE)
        try:    
            address = json_data['address']
            m = json_data['m']
        except:
            response = {
                'status': 'Wrong inputs.',
                'message': 'no address or in wrong data type'
            }
            return JsonResponse(response, status=status.HTTP_406_NOT_ACCEPTABLE)
        # optional parameters
        try:
            oracle_list = json_data['oracles']
        except:
            oracle_list = []

        try:
            oracle_list = self._get_oracle_list(oracle_list)
            multisig_addr, multisig_script, url_map_pubkeys = self._get_multisig_addr(oracle_list, source_code, m)
            compiled_code, interface = self._compile_code_and_interface(source_code)
            code = json.dumps({'source_code': compiled_code, 'multisig_addr' : multisig_addr})
        except Compiled_error as e:
            response = {
                'code:': ERROR_CODE['compiled_error'],
                'message': str(e)
            }
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)
        except Multisig_error as e:
            response = {
                'code': ERROR_CODE['multisig_error'],
                'message': str(e)
            }
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            tx_hex = OSSclient.deploy_contract_raw_tx(address, multisig_addr, code, CONTRACT_FEE)

            self._save_multisig_addr(multisig_addr, url_map_pubkeys)
            contract = Contract(
                    source_code = source_code,
                    multisig_address = multisig_addr,
                    multisig_script = multisig_script,
                    interface = interface,
                    color_id = 1,
                    amount = 0
            )
            contract.save()
            for i in oracle_list:
                contract.oracles.add(Oracle.objects.get(url=i["url"]))
            data = {
                "multisig_addr" : multisig_addr,
                "compiled_code" : compiled_code
            }
        except:
            response = {'status': 'Bad request.'}
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)

        response = {
            'multisig_address': multisig_addr,
            'oracles': oracle_list,
            'tx': tx_hex
        }
        return JsonResponse(response, status=status.HTTP_200_OK)


class ContractFunc(APIView):

    CONTRACTS_PATH = '../oracle/'  # collect contracts genertaed by evm under oracle directory
    HARDCODE_ADDRESS = '0x3510ce1b33081dc972ae0854f44728a74da9f291'
    EVM_COMMAND_PATH = '../go-ethereum/build/bin/evm'

    def _get_function_list(self, interface):

        if not interface:
            return []

        #The outermost quote must be ', otherwise json.loads will fail
        interface = json.loads(interface.replace("'", '"'))
        function_list = []
        for i in interface:
            if i['type'] == 'function':
                function_list.append({
                    'id': i['id'],
                    'name': i['name'],
                    'inputs': i['inputs']
                })

        return function_list

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

    def _evm_input_code(self, function, function_values):
        function_name = function['name'] + '('
        for i in function['inputs']:
             function_name += i['type'] + ','
        if(len(function['inputs']) != 0):
            function_name = function_name[:-1] + ')'
        else:
            function_name = function_name + ')'
        # Not sure why encode
        function_name = function_name.encode()
        k = sha3.keccak_256()
        k.update(function_name)

        input_code = k.hexdigest()[:8]
        for i in function_values:
            i = hex(int(i))[2:]
            input_code += '0'*(64-len(i)) + i
        return input_code

    def get(self, request, multisig_address):
        '''
        Get a list of functions of the given contract
        return format
        [
          {
            'id': 1,
            'name': 'function1',
            'inputs':'[
                 { 'name': name1, 'type': type1}, {'name': name2, 'type': type2}, ...
            ]'
          }, ...
        ]
        '''
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
        except Contract.DoesNotExist:
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.NOT_FOUND)
        function_list = self._get_function_list(contract.interface)
        response = {'functions': function_list}
        return JsonResponse(response, status=httplib.OK)



    def post(self, request, multisig_address):
        '''   
        This function will make a tx (user transfer money to multisig address)
        of contract type and op_return=function_inputs and function_id
        The oracle monitor will notice the created tx
        and then tunrs it to evn state
        
        inputs: from_address, to_address, amount, color, function_inputs, function_id
        `function_inputs` is a list
        '''

        json_data = json.loads(request.body.decode('utf8'))
        if json_data is not None:
            from_address = json_data['from_address']
            to_address = multisig_address
            amount = int(json_data['amount'])
            color = int(json_data['color'])
            function_name = json_data['function_name']
            function_inputs = json_data['function_inputs']

            try:
                contract = Contract.objects.get(multisig_address=multisig_address)
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
                "function_inputs_hash" : evm_input_code,
                "multisig_addr" : multisig_address
            })
            tx_hex = OSSclient.operate_contract_raw_tx(from_address, to_address, amount, color, code, CONTRACT_FEE)
            response = {'raw_tx': tx_hex}
            
            return JsonResponse(response)

        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class ContractList(APIView):
    def get(self, request, format=None):
        contracts = Contract.objects.all()
        serializer = ContractSerializer(contracts, many=True)
        response = {'contracts':serializer.data}
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