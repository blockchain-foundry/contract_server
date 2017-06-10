from django.db import models


class StateInfo(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    multisig_address = models.CharField(max_length=100, primary_key=True)
    latest_tx_time = models.CharField(max_length=100, blank=True, default='')
    latest_tx_hash = models.CharField(max_length=100, blank=True, default='')


class ContractInfo(models.Model):
    state_info = models.ForeignKey(StateInfo)
    multisig_address = models.CharField(max_length=100)
    contract_address = models.CharField(max_length=100)
