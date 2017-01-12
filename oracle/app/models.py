from datetime import datetime

from django.db import models


#class Oracle(models.Model):
#   created = models.DateTimeField(auto_now_add=True)
#   name = models.CharField(max_length=100, blank=True, default='')
#   url = models.TextField(validators=[URLValidator()])

#   class Meta:
#       ordering = ('created',)

class Keystore(models.Model):
    public_key    = models.CharField(max_length=100)
    private_key   = models.CharField(max_length=100)

class Proposal(models.Model):
    source_code   = models.TextField()
    public_key    = models.CharField(max_length=100)
    multisig_addr = models.CharField(max_length=100, blank=True)
    created       = models.DateTimeField(auto_now_add=True)
    address       = models.CharField(max_length=100)

    class Meta:
        ordering = ('public_key',)

class Registration(models.Model):
    proposal      = models.OneToOneField(Proposal)
    registrated   = models.DateTimeField(auto_now_add=True)
    multisig_address = models.CharField(max_length=100)
    redeem_script = models.CharField(max_length=256)

    class Meta:
        ordering = ('registrated',)
