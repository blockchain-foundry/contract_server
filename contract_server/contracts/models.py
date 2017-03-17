from django.db import models
from oracles.models import Oracle


class MultisigAddress(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    address = models.CharField(max_length=100, blank=True, default='')
    script = models.CharField(max_length=4096, blank=True, default='')
    oracles = models.ManyToManyField(Oracle)
    least_sign_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('created',)


class Contract(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    source_code = models.TextField()
    color = models.PositiveIntegerField()
    amount = models.PositiveIntegerField()
    interface = models.TextField(default='')
    contract_address = models.CharField(max_length=100, blank=True, default='')
    multisig_address = models.ForeignKey(MultisigAddress)

    class Meta:
        ordering = ('created',)
