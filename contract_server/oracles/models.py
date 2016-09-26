from django.core.validators import URLValidator
from django.db import models


class Contract(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    source_code = models.TextField()
    contract_id = models.CharField(max_length=100)
    color_id = models.PositiveIntegerField()
    amount = models.PositiveIntegerField()
    multisig_address = models.CharField(max_length=100, blank=True, default='')
    interface = models.TextField(default='')
    class Meta:
        ordering = ('created',)

class Oracle(models.Model):
    contract = models.ForeignKey(Contract, related_name='oracles')
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    url = models.URLField()
    class Meta:
        ordering = ('created',)

