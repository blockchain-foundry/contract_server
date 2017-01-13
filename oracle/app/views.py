import json
from binascii import hexlify
from subprocess import check_call
from django.http import HttpResponse, JsonResponse

import base58
from rest_framework import status
from rest_framework.views import APIView
import gcoinrpc
from app.models import Proposal, Registration, Keystore
from app.serializers import ProposalSerializer, RegistrationSerializer
from gcoin import *
from .deploy_contract_utils import *
from django.utils.crypto import get_random_string

try:
    import http.client as httplib
except ImportError:
    import httplib

EVM_PATH = '../oracle/states/{multisig_address}'

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

        private_key = sha256(get_random_string(64,'0123456789abcdef'))
        public_key = privtopub(private_key)
        address = pubtoaddr(public_key)
        p = Proposal(source_code=source_code, public_key=public_key, address=address)
        k = Keystore(public_key=public_key, private_key=private_key)
        p.save()
        k.save()

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


class Sign(APIView):

    def post(self, request):
        data = request.POST
        tx = data['transaction']
        script = data['script']
        user_evm_address = wallet_address_to_evm(data['user_address'])
        # need to check contract result before sign Tx
        try:
            with open(EVM_PATH.format(multisig_address=data['multisig_address']), 'r') as f:
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

        #signature = connection.signrawtransaction(tx)
        p = Proposal.objects.get(multisig_addr=data['multisig_address'])
        private_key = Keystore.objects.get(public_key=p.public_key).private_key
        signature = signall_multisig(tx, script, [private_key])

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
