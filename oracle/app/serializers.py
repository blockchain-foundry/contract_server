from rest_framework import serializers

from app.models import Proposal


class ProposalSerializer(serializers.ModelSerializer):

    class Meta:
        model = Proposal
        fields = ('source_code', 'public_key', 'created')
