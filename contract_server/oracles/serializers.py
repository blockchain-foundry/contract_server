from rest_framework import serializers
from oracles.models import Oracle

class OracleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Oracle
        fields = ('created', 'name', 'url')
