from rest_framework import serializers
from events.models import Watch


class WatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Watch
        fields = ('created', 'key', 'subscription_id',
                  'args', 'is_closed', 'is_expired', 'hashed_key')
