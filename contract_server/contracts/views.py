import json
import base58
from binascii import hexlify

from subprocess import PIPE, STDOUT, Popen, check_call, CalledProcessError
from threading import Thread

import requests
import sha3
from django.http import JsonResponse
from django.conf import settings
from rest_framework.views import APIView, status

import gcoinrpc
from gcoin import *
from oracles.models import Oracle
from oracles.serializers import *

from .forms import ContractFunctionPostForm

try:
    import http.client as httplib
except ImportError:
    import httplib



# Create your views here.

class Contracts(APIView):

    BITCOIN = 100000000 # 1 bitcoin == 100000000 satoshis
    CONTRACT_FEE = 1 # 1 bitcoin
    TX_FEE = 1 # 1 bitcoin, either 0 or 1 is okay.
    FEE_COLOR = 1
    CONTRACT_TX_TYPE = 5
    SOLIDITY_PATH = "../solidity/build/solc/solc"

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
            print(response)
            return JsonResponse(response)
        except:
            response = {'status': 'contract not found.'}
            return JsonResponse(
                    json_data['multisig_address'],
                    status=status.HTTP_404_NOT_FOUND
            )

    def _select_utxo(self, address):

        c = gcoinrpc.connect_to_local()
        utxos = c.gettxoutaddress(address)
        for i in utxos:
            if (i['color'] == self.FEE_COLOR and
                    i['value'] > self.CONTRACT_FEE + self.TX_FEE):
                return (i['txid'], i['vout'], i['scriptPubKey'], i['value'],
                       i['color']
                )
        raise ValueError(
            'Insufficient funds in address %s to create a contract.' % address
        )

    def _get_pubkey_from_oracle(self, url, source_code, pubkeys):
        '''
            get public keys from an oracle
        '''

        data = {
            'source_code': source_code
        }
        r = requests.post(url + '/proposals/', data=json.dumps(data))
        pubkey = json.loads(r.text)['public_key']
        pubkeys.append(pubkey)

    def _get_multisig_addr(self, oracle_list, source_code, m):
        """
            get public keys and create multisig_address
        """

        if len(oracle_list) < m:
            raise ValueError("The m in 'm of n' is bigger than n.")
        pubkeys = []
        threads = []
        for oracle in oracle_list:
            t = Thread(target=self._get_pubkey_from_oracle,
                    args=(oracle['url'], source_code, pubkeys)
            )
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        script = mk_multisig_script(pubkeys, m)
        multisig_addr = scriptaddr(script)
        return multisig_addr

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
        p = Popen(command, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        r = str(p.communicate(input=bytes(source_code, "utf8"))[0], "utf8")
        r = r.strip()
        if p.returncode != 0:
            raise ValueError("Error occurs when compiling source code.")
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

    def _make_contract_tx(self, txid, vout, script, address, value, color,
            multisig_addr, code):

        # 1. We must ensure that value is int type,
        #    otherwise errors will occur in make_raw_tx().
        # 2. In raw transaction, we use satoshis as the standard unit.
        value = int(value * self.BITCOIN)

        if value <= (self.TX_FEE + self.CONTRACT_FEE) * self.BITCOIN:
            raise ValueError("Insufficient funds.")

        inputs = [{ # txid, vout, script, multisig_addr, bytecode
            'tx_id': txid,
            'index': vout,
            'script': script
        }]
        op_return_script = mk_op_return_script(code)
        outputs = [
            {
                'address': address,
                'value': value - (self.CONTRACT_FEE + self.TX_FEE) * self.BITCOIN,
                'color': color
            },
            {
                'address': multisig_addr,
                'value': self.CONTRACT_FEE * self.BITCOIN,
                'color': color
            },
            {
                'script': op_return_script,
                'value': 0,
                'color': 0
            }
        ]
        tx_hex = make_raw_tx(inputs, outputs, self.CONTRACT_TX_TYPE)
        return tx_hex

    def post(self, request):

        # required parameters
        try:
            body_unicode = request.body.decode('utf-8')
            json_data = json.loads(body_unicode)
            source_code = str(json_data['source_code'])
            address = json_data['address']
            m = json_data['m']
        except:
            response = {'status': 'Bad request.'}
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)
        # optional parameters
        try:
            oracle_list = json_data['oracles']
        except:
            oracle_list = []

        try:
            oracle_list = self._get_oracle_list(oracle_list)
            multisig_addr = self._get_multisig_addr(oracle_list, source_code, m)
            compiled_code, interface = self._compile_code_and_interface(source_code)
            txid, vout, script, value, color = self._select_utxo(address)
            tx_hex = self._make_contract_tx(
                    txid, vout, script, address, value, color,
                    multisig_addr, compiled_code
            )

            oracles = []
            for i in oracle_list:
                oracles.append(i["url"])
            oracles = ','.join(oracles)

            contract = Contract(
                    source_code = source_code,
                    multisig_address = multisig_addr,
                    oracles = oracles,
                    interface = interface
            )
            contract.save()
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

    HARDCODE_ADDRESS = '0x3510ce1b33081dc972ae0854f44728a74da9f291'
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

    def _get_function_by_id(self, interface, function_id):
        '''
        interface is string of a list of dictionary containing id, name, type, inputs and outputs
        '''
        if not interface:
            return {}

        interface = json.loads(interface.replace("'", '"'))
        for i in interface:
            fid = i.get('id')
            if fid == function_id and i['type'] == 'function':
                return i
        return {}

    def _evm_input_code(self, function, function_values):
        function_name = function['name'] + '('
        for i in function['inputs']:
             function_name += i['type'] + ','
        function_name = function_name[:-1] + ')'
        # Not sure why encode
        function_name = function_name.encode()
        k = sha3.keccak_256()
        k.update(function_name)

        input_code = ' --input ' + k.hexdigest()[:8]
        for i in function_values:
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
        Execute the given function in the given contract with the given arguments
        Input format:
        {
          'function_id': function_id,
          'function_inputs': [
            {
              'name': name,
              'type': type,
              'value': value,
            },
          ]
        }
        '''
        form = ContractFunctionPostForm(request.POST)
        if form.is_valid():
            function_id = form.cleaned_data['function_id']
            function_inputs = form.cleaned_data['function_inputs']
            try:
                contract = Contract.objects.get(multisig_address=multisig_address)
            except Contract.DoesNotExist:
                response = {'error': 'contract not found'}
                return JsonResponse(response, status=httplib.NOT_FOUND)

            function = self._get_function_by_id(contract.interface, function_id)
            if not function:
                response = {'error': 'function not found'}
                return JsonResponse(response, status=httplib.NOT_FOUND)

            input_value = []
            for i in function_inputs:
                input_value.append(i['value'])
            evm_input_code = self._evm_input_code(function, input_value)

            r = requests.get(settings.OSS_API_URL+'/base/v1/balance/{address}'.format(address=multisig_address))
            value = json.dumps(r.json())
            value = "'" + value + "'"
            # Hard code sender address for it is not actually used
            multisig_address_hex = base58.b58decode(multisig_address)
            multisig_address_hex = hexlify(multisig_address_hex)
            multisig_address_hex = "0x" + hash160(multisig_address_hex)
            command = "../go-ethereum/build/bin/evm" + " --read " + multisig_address + " --sender " + self.HARDCODE_ADDRESS + " --fund " + value + " --value " + value + evm_input_code + " --dump " + "--receiver " + multisig_address_hex
            try:
                check_call(command, shell=True)
            except CalledProcessError:
                # TODO logger
                response = {'error': 'internal server error'}
                return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)

            response = {'status': 'success'}
            return JsonResponse(response, status=httplib.OK)

        response = {'error': form.errors}
        return JsonResponse(response, status=httplib.BAD_REQUEST)


class ContractList(APIView):
    def get(self, request, format=None):
        contracts = Contract.objects.all()
        serializer = ContractSerializer(contracts, many=True)
        response = {'contracts':serializer.data}
        return JsonResponse(response)
