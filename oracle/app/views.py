import json
from binascii import hexlify
from subprocess import check_call
from django.http import HttpResponse, JsonResponse

import base58
from rest_framework import status
from rest_framework.views import APIView
import gcoinrpc
from app.models import Proposal, Registration
from app.serializers import ProposalSerializer, RegistrationSerializer
from gcoin import *
from .deploy_contract_utils import *


try:
    import http.client as httplib
except ImportError:
    import httplib


def wallet_address_to_evm(address):
    address = base58.b58decode(address)
    address = hexlify(address)
    address = hash160(address)
    return address


class Proposes(APIView):
    """
    Give the publicKey when invoked.


    """

    def post(self, request):
        # Return public key to Contract-Server
        body_unicode = request.body.decode('utf-8')
        
        json_data = json.loads(body_unicode)
        try:
            source_code = json_data['source_code']
        except:
            response = {'status': 'worng argument'}
            return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST, content_type="application/json")

        connection = gcoinrpc.connect_to_local()  
        connection.keypoolrefill(1)
        address = connection.getnewaddress()
        public_key = connection.validateaddress(address).pubkey
        p = Proposal(source_code=source_code, public_key=public_key, address=address)
        p.save()

        response = {'public_key': public_key}
        return JsonResponse(response, status=httplib.OK)


class Multisig_addr(APIView):

    def post(self, request):
        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)
        try:
            pubkey = json_data['pubkey']
            multisig_addr = json_data['multisig_addr']
        except:
            response = {'status': 'worng argument'}
            return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST, content_type="application/json")

        p = Proposal.objects.get(public_key=pubkey)
        p.multisig_addr = multisig_addr
        p.save()
        response = {
            "status": "success"
        }
        return JsonResponse(response)


class Registrate(APIView):

    def post(self, request):
        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)

        try:
            public_key = json_data['public_key']
            p = Proposal.objects.get(public_key=json_data['public_key'])
            multisig_address = json_data['multisig_address']
            redeem_script = json_data['redeem_script']
            r = Registration(proposal=p, multisig_address=multisig_address,
                             redeem_script=redeem_script)
            r.save()
        except:
            response = {'status': 'worng argument'}
            return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST, content_type="application/json")

        response = {'status': 'success'}
        return HttpResponse(json.dumps(response), content_type="aplication/json")


#  TODO: to be removed
class Deploy(APIView):

    def post(self, request):
        EVM_PATH = "../go-ethereum/build/bin/evm"
        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)
        compiled_code = str(json_data["compiled_code"])
        multisig = str(json_data["multisig_addr"])
        multisig_hex = base58.b58decode(multisig)
        multisig_hex = hexlify(multisig_hex)
        multisig_hex = "0x" + hash160(multisig_hex)
        # TODO:  Oracle should be careful writing the state file, cause it'll
        # change the state of the contract, which matters when the user want their
        # money back.
        command = [EVM_PATH, "--deploy", "--write", multisig,
                   "--code", compiled_code, "--receiver", multisig_hex]
        response = {}
        try:
            check_call(command)
            response = {
                "status": "success"
            }
            return JsonResponse(response)
        except Exception as e:
            print(e)
            response = {
                "status": "fail"
            }
        return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)


class Sign(APIView):

    EVM_PATH = '../oracle/{multisig_address}'

    def post(self, request):
        data = request.POST
        tx = data['transaction']
        script = data['script']
        user_evm_address = wallet_address_to_evm(data['user_address'])
        # need to check contract result before sign Tx
        try:
            with open(self.EVM_PATH.format(multisig_address=data['multisig_address']), 'r') as f:
                content = json.load(f)
                account = content['accounts'][user_evm_address]
                if not account:
                    response = {'error': 'Address not found'}
                    return JsonResponse(response, status=httplib.NOT_FOUND)
                amount = account['balance'][data['color_id']]
        except IOError:
            # Log
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)
        if int(amount) < int(data['amount']):
            response = {'error': 'insufficient funds'}
            return JsonResponse(response, status=httplib.BAD_REQUEST)
        connection = gcoinrpc.connect_to_local()
        #signature = connection.signrawtransaction(tx)
        p = Proposal.objects.get(multisig_addr=data['multisig_address'])
        privkeys = [connection.dumpprivkey(p.address)]
        signature = signall_multisig(tx, script, privkeys)
        # return only signature hex
        response = {'signature': signature}
        return JsonResponse(response, status=httplib.OK)


class ProposalList(APIView):

    def get(self, request):
        proposals = Proposal.objects.all()
        serializer = ProposalSerializer(proposals, many=True)
        response = {'proposal': serializer.data}
        return HttpResponse(json.dumps(response), content_type="application/json")


class RegistrationList(APIView):

    def get(self, request):
        registrations = Registration.objects.all()
        serializer = RegistrationSerializer(registrations, many=True)
        response = {'registration': serializer.data}
        return HttpResponse(json.dumps(response), content_type="application/json")


class GetBalance(APIView):

    def get(self, request, multisig_address, address):
        EVM_PATH = '../oracle/' + multisig_address
        user_evm_address = wallet_address_to_evm(address)
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                account = content['accounts'][user_evm_address]
                amount = account['balance']
                response = amount
                return JsonResponse(response, status=httplib.OK)
        except:
            response = {}
            return JsonResponse(response, status=httplib.OK)


class GetStorage(APIView):

    def get(self, request, multisig_address):
        EVM_PATH = '../oracle/' + multisig_address
        contract_evm_address = wallet_address_to_evm(multisig_address)
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                account = content['accounts'][contract_evm_address]
                storage = account['storage']
                response = storage
                return JsonResponse(response, status=httplib.OK)
        except:
            response = {}
            return JsonResponse(response, status=httplib.OK)


class CheckContractCode(APIView):

    def get(self, request, multisig_address):
        EVM_PATH = '../oracle/' + multisig_address
        contract_evm_address = wallet_address_to_evm(multisig_address)
        try:
            with open(EVM_PATH.format(multisig_address=multisig_address), 'r') as f:
                content = json.load(f)
                account = content['accounts'][contract_evm_address]
                code = account['code']
                response = {'code': code}
                return JsonResponse(response, status=httplib.OK)
        except:
            response = {'status': 'Contract code not found'}
            return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)


class NewTxNotified(APIView):

    def post(self, request, tx_hash):
        response = {}
        print('ok, received notify with tx_hash ' + tx_hash)
        deploy_contracts(tx_hash)

        response['data'] = 'ok, received notify with tx_hash ' + tx_hash
        return JsonResponse(response, status=httplib.OK)
