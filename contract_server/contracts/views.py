import json
import subprocess
from queue import Queue
from threading import Thread

import requests
import sha3  # keccak_256
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date
from rest_framework.views import APIView, status

import gcoinrpc
from oracles.models import *
from oracles.serializers import *


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

    def post(self, request):
        def getPublicKeys(server_queue, keys, source_code,oracle_key):
            url = (server_queue.get())['url']
            data = {'source_code':source_code}
            request_key = requests.post(url + "/proposals/", data=json.dumps(data))
            key = json.loads(request_key.text)['public_key']
            oracle_key.append((key,url))
            keys.append(key)
            server_queue.task_done()

        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)
        min_authority = 1
        oracles_num = 1
        serverlist = list(Oracle.objects.all())
        try:
            source_code = str(json_data['source_code'])
            #get valid term start and end
            try:
                valid_start = parse_date(json_data['valid_term_start'])
            except:
                pass
            try:
                valid_end   = parse_date(json_data['valid_term_end'])
            except:
                pass

            #compile soure code
            # return : binary, ABI

            #1. store source code to file
            file = open('compile','w')
            file.write(source_code)
            file.close()

            #2. compile: solc filename --abi --bin
            command = "../solidity/solc/solc compile --abi --bin"
            r = str(subprocess.check_output(command, shell = True), "utf8").strip()
            str1 = r.split('Binary:')
            str2 = str1[1].split('\n')
            binary = str2[1]
            abi = str2[3]
        except:
            response = {'status':'worng arguments.'}
            return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST, content_type="application/json")

        try:
            for oracle in json_data['oracles']:
                serverlist.append(oracle)
        except:
            response = {'status':'oracle not found.'}
            return HttpResponse(json.dumps(response),status=status.HTTP_404_NOT_FOUND, content_type="application/json")

        serverlist.reverse() #oracle list
        server_queue=Queue()
        keys = []
        source_code = json_data['source_code']
        oracle_key=[]
        for server in serverlist[:oracles_num]:
            worker = Thread(target=getPublicKeys, args=(server_queue, keys, source_code,oracle_key))
            worker.start()
            server_queue.put(server)
        server_queue.join()

        c = gcoinrpc.connect_to_local()
        try:
            multisig = c.createmultisig(min_authority, keys)
        except:
            #createmultisig failed
            pass

        command = "../go-ethereum/build/bin/evm --jonah --write " + multisig['address'] + " --code " + binary +" --receiver " + multisig['address']
        subprocess.check_output(command, shell = True)
        abi = json.loads(abi)
        interface = []
        ids = 1
        for func in abi:
            try:
                func['id'] = ids
                interface.append(func)
                ids = ids + 1
            except:
                pass

        contract = Contract(valid_term_start=valid_start, valid_term_end=valid_end, source_code=source_code,multisig_address=multisig['address'], oracles=serverlist[:oracles_num], interface=interface)
        contract.save()

        for url in oracle_key:
            data = {'multisig_address':multisig['address'],'public_key':url[0],'redeem_script':multisig['redeemScript'], 'valid_term_start':valid_start, 'valid_term_end':valid_end}
            print(data)
            request_registration = requests.post(url[1] + "/registration/", data=json.dumps(data))

        seri_oracle = OracleSerializer(contract.oracles, many=True)
        response = {'multisig_address': multisig['address'], 'oracles':seri_oracle.data, 'interface':interface}
        return HttpResponse(json.dumps(response), content_type="application/json")

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
