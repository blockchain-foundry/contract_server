from oracles.models import Oracle
from oracles.serializers import OracleSerializer
from rest_framework import mixins
from rest_framework import generics

class OracleList(mixins.ListModelMixin, mixins.CreateModelMixin, generics.GenericAPIView):
    queryset = Oracle.objects.all()
    serializer_class = OracleSerializer
    
    def get(self, request):
        return self.list(request)
