from django.db import models
from oracles.models import Oracle
import hashlib

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
    tx_hash_init = models.CharField(max_length=200, blank=True, default='')
    hash_op_return = models.IntegerField(default=-1)
    sender_evm_address = models.CharField(max_length=100, blank=True, default='')
    sender_nonce_predicted = models.IntegerField(default=-1)
    is_deployed = models.BooleanField(default=False)

    @classmethod
    def make_hash_op_return(cls, op_return):
        print("*********")
        print(op_return)
        return int(hashlib.sha1(op_return.encode('utf-8')).hexdigest(), 16) % (2 ** 31)

    class Meta:
        ordering = ('created',)
