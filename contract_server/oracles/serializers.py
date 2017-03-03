from rest_framework import serializers

from oracles.models import *


class OracleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Oracle
        fields = ('created', 'name', 'url')


class ContractSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contract
        fields = ('created', 'source_code', 'multisig_address', 'interface', 'oracles')


class SubContractSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubContract
        fields = ('parent_contract', 'deploy_address',
                  'source_code', 'color_id', 'amount', 'interface')
