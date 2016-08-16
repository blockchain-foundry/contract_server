from oracles.models import Oracle
from oracles.serializers import OracleSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
import json

class OracleList(APIView):
	def get(self, request, format=None):
		oracles = Oracle.objects.all()
		serializer = OracleSerializer(oracles, many=True)
		response = {'oralces':serializer.data}
		return HttpResponse(json.dumps(response), content_type="application/json")
class AddOracle(APIView):
	def get(self,request):
		o = Oracle(name='http://localhost:8080', url='http://localhost:8080')	
		o.save()
		try:
			response = {'add in list': 'ture'}
		except:
			response = {'add in list':'false'}
		return HttpResponse(json.dumps(response), content_type="application/json")
		
