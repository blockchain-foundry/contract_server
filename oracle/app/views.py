import json
import base58
from binascii import hexlify
from rest_framework import status
from rest_framework.views import APIView

import gcoinrpc
from gcoin import *
from subprocess import check_call
from app.models import Proposal, Registration
from app.serializers import ProposalSerializer, RegistrationSerializer

try:
    import http.client as httplib
except ImportError:
    import httplib





class Proposes(APIView):

    def post(self, request):
        # Return public key to Contract-Server
        data = request.POST
        source_code = data['source_code']

        connection = gcoinrpc.connect_to_local()
        connection.keypoolrefill(1)
        address = connection.getnewaddress()
        public_key = connection.validateaddress(address)['pubkey']

        p = Proposal(source_code=source_code, public_key=public_key)
        p.save()
        response = {'public_key':public_key}
        return JsonResponse(response, status=httplib.OK)

class Registrate(APIView):
    def post(self, request):
        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)

        try:
            public_key = json_data['public_key']
            p = Proposal.objects.get(public_key=json_data['public_key'])
            multisig_address = json_data['multisig_address']
            redeem_script = json_data['redeem_script']
            r = Registration(proposal=p, multisig_address=multisig_address, redeem_script=redeem_script)
            r.save()
        except:
            response = {'status':'worng argument'}
            return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST, content_type="application/json")

        response = {'status':'success'}
        return HttpResponse(json.dumps(response), content_type="aplication/json")

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
        command = [EVM_PATH, "--deploy", "--write", multisig, "--code", compiled_code, "--receiver", multisig_hex]
        response = {}
        try:
            check_call(command)
            response = {
                "status":"success"    
            }
            return JsonResponse(response)
        except Exception as e:
            print(e)
            response = {
                "status":"fail"
            }
        return JsonResponse(response, status=status.HTTP_400_BAD_REQUEST)

class Sign(APIView):

    def post(self, request):
        data = request.POST
        tx = data['transaction']
        #need to check contract result before sign Tx
        with open('../../go-ethereum/{contract_id}'.format(contract_id=data['contract_id']), 'r') as f:
            content = json.load(f)
            account = content['accounts'].get(data['address'])
            if not account:
                response = {'error': 'Address not found'}
                return JsonResponse(response, status=httplib.NOT_FOUND)
            amount = account['balance'].get(data['color_id'], 0)

        except IOError:
            # Log
            response = {'error': 'contract not found'}
            return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)

        if amount < data['amount']:
            response = {'error': 'insufficient funds'}
            return JsonResponse(response, status=httplib.BAD_REQUEST)
        signature = connection.signrawtransaction(tx)
        # return only signature hex
        response = {'signature': signature['hex']}
        return JsonResponse(response, status=httplib.OK)


class ProposalList(APIView):
    def get(self, request):
        proposals = Proposal.objects.all()
        serializer = ProposalSerializer(proposals, many=True)
        response = {'proposal': serializer.data}
        return HttpResponse(json.dumps(response), content_type = "application/json")
class RegistrationList(APIView):
    def get(self, request):
        registrations = Registration.objects.all()
        serializer = RegistrationSerializer(registrations, many=True)
        response = {'registration': serializer.data}
        return HttpResponse(json.dumps(response), content_type = "application/json")
