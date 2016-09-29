from django.core.validators import URLValidator
from django.db import models


class Contract(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    source_code = models.TextField()
    multisig_address = models.CharField(max_length=100, blank=True, default='')
    interface = models.TextField(default='')
    oracles = models.TextField(default='')
    class Meta:
        ordering = ('created',)

class Oracle(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    url = models.TextField(validators=[URLValidator()])
    class Meta:
        ordering = ('created',)
