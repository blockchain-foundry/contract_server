from rest_framework import status
from rest_framework.views import APIView
from django.http import HttpResponse
from app.models import Proposal, Registration
from app.serializers import ProposalSerializer, RegistrationSerializer
import json
import gcoinrpc


class Proposes(APIView):

	def post(self, request):
		body_unicode = request.body.decode('utf-8')
		json_data = json.loads(body_unicode)
		try:
			source_code = json_data['source_code']
		except:
			response = {'status':'worng argument'}
			return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST,  content_type="application/json")
		
		connection = gcoinrpc.connect_to_local()
		connection.keypoolrefill(1)
		public_key = connection.getnewaddress() 		
		p1 = Proposal(source_code= source_code,public_key= public_key)	
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
			multisig_address=json_data['multisig_address']
			redeem_script=json_data['redeem_script']
			r = Registration(proposal = p , multisig_address=multisig_address, redeem_script=redeem_script)
			r.save()
	
		except:
			response = {'status':'worng argument'}
			return HttpResponse(json.dumps(response), status=status.HTTP_400_BAD_REQUEST,  content_type="application/json")
	
		response = {'status':'success'}
		return HttpResponse(json.dumps(response), content_type="aplication/json")


		

class Sign(APIView):
	
	def post(self, request):
		connection = gcoinrpc.connect_to_local()
		body_unicode = request.body.decode('utf-8')
		json_data = json.loads(body_unicode)
		hexTx= json_data['transaction']
		try:
			#need to check contract result before sign Tx
			signature = connection.signrawtransaction(hexTx)
			# return only signature hex
			response = {'signature': signature['hex']}
			return HttpResponse(json.dumps(response), content_type="application/json")
		except:
			response = {'status':'contract not found'}
			return HttpResponse(json.dumps(response), status=status.HTTP_404_NOT_FOUND,  content_type="application/json")


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


