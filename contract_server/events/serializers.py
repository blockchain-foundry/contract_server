from rest_framework import serializers
from events.models import Watch


class WatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Watch
        fields = ('created', 'id', 'event_name',
                  'args', 'is_closed', 'is_expired', 'hashed_event_name',
                  'contract_address')


class CreateWatchSerializer(serializers.Serializer):
    multisig_address = serializers.CharField(max_length=100)
    event_name = serializers.CharField(max_length=300)
    contract_address = serializers.CharField(max_length=100)
    conditions = serializers.CharField(max_length=300, required=False)
