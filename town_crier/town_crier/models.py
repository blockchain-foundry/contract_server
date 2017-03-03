from django.db import models

class Keystore(models.Model):
    address = models.CharField(max_length=100)
    private_key = models.CharField(max_length=100)
    contract_address = models.CharField(max_length=100)
    sender_address = models.CharField(max_length=100)
    url = models.CharField(max_length=100)
