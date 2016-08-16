from oracles.models import Oracle, Contract
from oracles.serializers import OracleSerializer, ContractSerializer
from django.shortcuts import render
from rest_framework.views import status
from rest_framework.views import APIView
from django.http import HttpResponse
from threading import Thread
from queue import Queue
import requests
import subprocess
import json
import gcoinrpc

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

	def post(self, request):
		def getPublicKeys(server_queue, keys, source_code):
			url = (server_queue.get())['url']
			data = {'source_code':source_code}
			request_key = requests.post(url + "/proposals/", data=json.dumps(data))
			keys.append(json.loads(request_key.text)['public_key'])
			server_queue.task_done()
	
		body_unicode = request.body.decode('utf-8')
		json_data = json.loads(body_unicode)	
		min_authority = 1
		oracles_num = 1
		#serverlist = OracleSerializer(ser, many=True)
		serverlist = list(Oracle.objects.all())
		try: 
			source_code = json_data['source_code']
		except:
			response = {'status':'worng arguments.'}
			return HttpResponse(json.dumps(reponse), status=status.HTTP_400_BAD_REQUEST, content_type="application/json")
		
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

		for server in serverlist[:oracles_num]:
			worker = Thread(target=getPublicKeys, args=(server_queue, keys, source_code))
			worker.start()
			server_queue.put(server)
		server_queue.join()
		
		c = gcoinrpc.connect_to_local()
		try:
			multisig = c.createmultisig(min_authority, keys)
		except:
			pass
		contract = Contract(source_code=source_code,multisig_address=multisig['address'], oracles=serverlist[:oracles_num])
		contract.save()

		serializer = OracleSerializer(contract.oracles, many=True)
		response = {'multisig_address': multisig['address'], 'oracles':serializer.data}
		return HttpResponse(json.dumps(response), content_type="application/json")
	

class ContractFunc(APIView):
	def post(self, request, multisig_address):
		try:
			contract = Contract.objects.get(multisig_address=multisig_address)
		except:
			response = {'status': 'contract not found.'}
			return HttpResponse(json.dumps(response),status=status.HTTP_404_NOT_FOUND, content_type="application/json")
		
		try:
			#get function
			r = 'r'
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
