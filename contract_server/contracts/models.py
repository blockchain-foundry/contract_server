import hashlib

from django.conf import settings
from django.db import models, IntegrityError

from gcoinapi.client import GcoinAPIClient
from oracles.models import Oracle

from .exceptions import SubscribeAddrsssNotificationError

OSSclient = GcoinAPIClient(settings.OSS_API_URL)


class MultisigAddress(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    address = models.CharField(max_length=100, blank=True, default='')
    script = models.CharField(max_length=4096, blank=True, default='')
    oracles = models.ManyToManyField(Oracle)
    least_sign_number = models.PositiveIntegerField(default=1)
    is_state_multisig = models.BooleanField(default=False)

    class Meta:
        ordering = ('created',)

    def __str__(self):
        return self.address

    def save(self, *args, **kwargs):
        # Subscribe notification
        if self.is_state_multisig:
            callback_url = self._get_callback_url(self.address)
            try:
                _, _ = OSSclient.subscribe_address_notification(
                    self.address, callback_url)
            except Exception as e:
                print(str(e) + ', SubscribeAddrsssNotificationError')
                raise SubscribeAddrsssNotificationError('SubscribeAddrsssNotificationError')

        return super(MultisigAddress, self).save(*args, **kwargs)

    def _get_callback_url(self, multisig_address):
        callback_url = settings.CONTRACT_SERVER_API_URL + '/addressnotify/' + multisig_address
        callback_url = ''.join(callback_url.split())
        return callback_url


class Contract(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    source_code = models.TextField()
    color = models.PositiveIntegerField()
    amount = models.PositiveIntegerField()
    interface = models.TextField(default='')
    contract_address = models.CharField(max_length=100, blank=True, default='')
    contract_multisig_address = models.ForeignKey(MultisigAddress, blank=True, null=True, related_name='contract')
    state_multisig_address = models.ForeignKey(MultisigAddress, related_name='contract_set', null=True)
    tx_hash_init = models.CharField(max_length=200, blank=True, default='')
    hash_op_return = models.IntegerField(default=-1)
    sender_evm_address = models.CharField(max_length=100, blank=True, default='')
    is_deployed = models.BooleanField(default=False)

    @classmethod
    def make_hash_op_return(cls, op_return):
        return int(hashlib.sha1(op_return.encode('utf-8')).hexdigest(), 16) % (2 ** 31)

    class Meta:
        ordering = ('created',)

    def save(self, *args, **kwargs):
        # Subscribe notification
        if self.is_deployed and not self.contract_multisig_address:
            raise IntegrityError('Deployed contract must have a contract multisig address.')

        return super(Contract, self).save(*args, **kwargs)

    def as_dict(self):
        return {
            'state_multisig_address': self.state_multisig_address.address,
            'contract_multisig_address': self.contract_multisig_address.address,
            'contract_address': self.contract_address,
            'source_code': self.source_code,
            'is_deployed': self.is_deployed,
        }
