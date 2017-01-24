from django.utils import timezone
from django.db import models
import sha3


def default_time():
    return timezone.now()


class Watch(models.Model):
    created = models.DateTimeField(default=default_time)
    multisig_address = models.CharField(max_length=100)
    key = models.CharField(max_length=200)
    subscription_id = models.CharField(max_length=100, blank=False)
    args = models.CharField(max_length=1000, blank=True, default="")
    is_closed = models.BooleanField(default=False)

    @property
    def hashed_key(self):
        """
        Hash key by Keccak-256
        """
        k = sha3.keccak_256()
        k.update(self.key.encode())
        return k.hexdigest()

    @property
    def is_expired(self):
        """
        The watching subscription would be expired after timedelta
        """
        return self.created > timezone.timedelta(minutes=10) + timezone.now()

    class Meta:
        ordering = ('created',)
