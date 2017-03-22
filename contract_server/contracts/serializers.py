from rest_framework import serializers
from contracts.models import MultisigAddress


class CreateMultisigAddressSerializer(serializers.Serializer):
    m = serializers.IntegerField()
    oracles = serializers.CharField()


class MultisigAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = MultisigAddress
        fields = ('created', 'id', 'address', 'script', 'oracles', 'least_sign_number')
