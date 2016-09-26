from rest_framework import serializers

from app.models import Proposal, Registration


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = ('source_code', 'public_key', 'created')

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ('proposal', 'registrated', 'multisig_address', 'redeem_script')
