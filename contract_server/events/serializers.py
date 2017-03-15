from rest_framework import serializers
from events.models import Watch


class WatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Watch
        fields = ('created', 'id', 'event_name',
                  'args', 'is_closed', 'is_expired', 'hashed_event_name',
                  'contract_address')
