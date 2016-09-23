import json
import random

import requests
import sha3 # keccak_256

import gcoinrpc

from oracles.models import *
from oracles.serializers import *
from django.shortcuts import render
from django.utils.dateparse import parse_date
from rest_framework.views import status
from rest_framework.views import APIView
from subprocess import Popen, PIPE, STDOUT
from django.http import HttpResponse
from threading import Thread
from queue import Queue

from gcoin import *

# Create your views here.

class Contracts(APIView):
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
            return HttpResponse(json.dumps(response),content_type="application/json")
        except:
            response = {'status': 'contract not found.'}
            return HttpResponse(json.dumps(json_data['multisig_address']), status=status.HTTP_404_NOT_FOUND, content_type="application/json")

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

        command = ["../solidity/build/solc/solc", "--abi", "--bin"]
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

        BITCOIN = 100000000 # 1 bitcoin == 100000000 satoshis
        CONTRACT_FEE = 1 * BITCOIN # 1 bitcoin
        TX_FEE = 1 * BITCOIN # 1 bitcoin, either 0 or 1 is okay.
        CONTRACT_TX_TYPE = 5

        value = value * BITCOIN

        if value < TX_FEE + CONTRACT_FEE:
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
                'value': value - CONTRACT_FEE - TX_FEE,
                'color': color
            },
            {
                'address': multisig_addr,
                'value': CONTRACT_FEE,
                'color': color
            },
            {
                'script': op_return_script,
                'value': 0,
                'color': 0
            }
        ]
        tx_hex = make_raw_tx(inputs, outputs, CONTRACT_TX_TYPE)
        return tx_hex

    def post(self, request):

        # required parameters
        try:
            body_unicode = request.body.decode('utf-8')
            json_data = json.loads(body_unicode)
            source_code = str(json_data['source_code'])
            m = json_data['m']
            txid = json_data['utxo']['txid']
            vout = json_data['utxo']['vout']
            script = json_data['utxo']['script']
            address = json_data['utxo']['address']
            value = json_data['utxo']['value']
            color = json_data['utxo']['color']
        except:
            response = {'status': 'Bad request.'}
            return HttpResponse(json.dumps(response),
                status=status.HTTP_400_BAD_REQUEST,
                content_type="application/json"
            )
        # optional parameters
        try:
            oracle_list = json_data['oracles']
        except:
            oracle_list = []

        try:
            oracle_list = self._get_oracle_list(oracle_list)
            multisig_addr = self._get_multisig_addr(oracle_list, source_code, m)
            compiled_code = self._compile_code(source_code)
            tx_hex = self._make_contract_tx(
                    txid, vout, script, address, value, color,
                    multisig_addr, compiled_code
            )
        except:
            response = {'status': 'Bad request.'}
            return HttpResponse(json.dumps(response),
                status=status.HTTP_400_BAD_REQUEST,
                content_type="application/json"
            )

        response = {
            'multisig_address': multisig_addr,
            'oracles': oracle_list,
            'tx': tx_hex
        }
        return HttpResponse(
            json.dumps(response),
            status=status.HTTP_200_OK,
            content_type="application/json"
        )


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
            return HttpResponse(json.dumps(response),status=status.HTTP_404_NOT_FOUND, content_type="application/json")
        val = []
        try:
            func_id = json_data['function_id']
            value = json_data['function_inputs']
            for v in value:
                try:
                    val.append(v['value'])
                except:
                    response = {'status': 'wrong arguments.'}
                    return HttpResponse(json.dumps(response),status=status.HTTP_400_BAD_REQUEST, content_type="application/json")
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
            return HttpResponse(json.dumps(response),status=status.HTTP_400_BAD_REQUEST, content_type="application/json")

        response = {'status':'success'}
        return HttpResponse(json.dumps(response), content_type="application/json")


class ContractList(APIView):
    def get(self, request, format=None):
                contracts = Contract.objects.all()
                serializer = ContractSerializer(contracts, many=True)
                response = {'contracts':serializer.data}
                return HttpResponse(json.dumps(response), content_type="application/json")


