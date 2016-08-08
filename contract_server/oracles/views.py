from oracles.models import Oracle
from oracles.serializers import OracleSerializer
from rest_framework.views import APIView
from rest_framework.response import Response

class OracleList(APIView):
    def get(self, request, format=None):
        oracles = Oracle.objects.all()
        serializer = OracleSerializer(oracles, many=True)
        return Response({ 'oracles': serializer.data })
