import json
from subprocess import Popen, PIPE, STDOUT
from threading import Thread

import requests
import sha3
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.views import status

import gcoinrpc
from gcoin import *
from oracles.models import Oracle
from oracles.serializers import *

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

    def _compile_code(self, source_code):

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
        return compiled_code_in_hex

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
            compiled_code = self._compile_code(source_code)
            txid, vout, script, value, color = self._select_utxo(address)
            tx_hex = self._make_contract_tx(
                    txid, vout, script, address, value, color,
                    multisig_addr, compiled_code
            )
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
    def post(self, request, multisig_address):
        def FuncParam(function, func_id, val):
            function = function[int(func_id)-1]
            functionName = function['name'] + '('
            inputs = function['inputs']
            for inp in inputs:
                try:
                    inputtype = inp['type']
                    functionName = functionName+inputtype+','
                except:
                    pass
            functionName = functionName[:-1]+')'
            functionName = functionName.encode()
            k = sha3.keccak_256()
            k.update(functionName)
            input_param = k.hexdigest()
            input_param = input_param[:8]
            input_param = ' --input ' + input_param
            for v in val :
                input_param = input_param + '0'*(64-len(v)) + v
            return input_param

        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)
        try:
            contract = Contract.objects.get(multisig_address=multisig_address)
            serializer=ContractSerializer(contract)
        except:
            response = {'status': 'contract not found.'}
            return JsonResponse(response, status=status.HTTP_404_NOT_FOUND)
        val = []
        try:
            func_id = json_data['function_id']
            value = json_data['function_inputs']
            for v in value:
                try:
                    val.append(v['value'])
                except:
                    response = {'status': 'wrong arguments.'}
                    return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)
        except:
            pass

        try:
            #get function
            #keccak hash
            function = serializer.data['interface']
            function = eval(function)
            input_param = FuncParam(function, func_id, val)
            command = "../go-ethereum/build/bin/evm --read "+multisig_address+ input_param + " --dump --receiver " + multisig_address
            subprocess.check_output(command, shell = True)
        except:
            response = {'status': 'wrong arguments.'}
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)

        response = {'status':'success'}
        return JsonResponse(response)


class ContractList(APIView):
    def get(self, request, format=None):
        contracts = Contract.objects.all()
        serializer = ContractSerializer(contracts, many=True)
        response = {'contracts':serializer.data}
        return JsonResponse(response)


