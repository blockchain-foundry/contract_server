import json
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.views import APIView

import gcoinrpc
from subprocess import check_call
from app.models import Proposal, Registration
from app.serializers import ProposalSerializer, RegistrationSerializer


class Proposes(APIView):

    def post(self, request):
        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)
        try:
            source_code = json_data['source_code']
        except:
            response = {'status':'worng argument'}
            return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST, content_type="application/json")

        connection = gcoinrpc.connect_to_local()
        connection.keypoolrefill(1)
        address = connection.getnewaddress()
        result = connection.validateaddress(address)
        public_key = result.pubkey
        p1 = Proposal(source_code=source_code,public_key=public_key)
        p1.save()
        response = {'public_key':public_key}
        return HttpResponse(json.dumps(response), content_type="application/json")

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
        command = [EVM_PATH, "--deploy", "--write", multisig, "--code", compiled_code, "--receiver", multisig]
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
        connection = gcoinrpc.connect_to_local()
        body_unicode = request.body.decode('utf-8')
        json_data = json.loads(body_unicode)
        hexTx = json_data['transaction']
        try:
            #need to check contract result before sign Tx
            signature = connection.signrawtransaction(hexTx)
            # return only signature hex
            response = {'signature': signature['hex']}
            return HttpResponse(json.dumps(response), content_type="application/json")
        except:
            response = {'status':'contract not found'}
            return HttpResponse(json.dumps(response), status=status.HTTP_404_NOT_FOUND, content_type="application/json")


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
