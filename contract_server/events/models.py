import sha3
import json
from django.utils import timezone
from django.db import models
from contracts.models import Contract


def default_time():
    return timezone.now()


class WatchManager(models.Manager):
    def alive_list(self):
        """Query for alive watches
        """
        return self.filter(
            is_closed=False and self.args is not None
        )


class Watch(models.Model):
    created = models.DateTimeField(default=default_time)
    event_name = models.CharField(max_length=200)
    args = models.CharField(max_length=5000, blank=True, default="")
    is_closed = models.BooleanField(default=False)
    contract = models.ForeignKey(Contract, related_name='watch', blank=True, null=True)
    conditions = models.CharField(max_length=5000, blank=True, default="")

    objects = WatchManager()

    @property
    def hashed_event_name(self):
        """Hash event_name by Keccak-256
        """
        k = sha3.keccak_256()
        k.update(self.event_name.encode())
        return k.hexdigest()

    @property
    def is_expired(self):
        """Check if the watch is expired
        The watching subscription would be expired after timedelta
        """
        return self.created > timezone.timedelta(minutes=10) + timezone.now()

    @property
    def is_triggered(self):
        """Check if the related event is triggered
        The args field is not blank means the event is triggered and written to logs.
        """
        return len(self.args) > 0

    @property
    def interface(self):
        """Event interface
        """
        interface = self._get_event_by_name(self.contract.interface)
        return interface

    @property
    def conditions_list(self):
        conditions_list = []
        if self.conditions != "":
            conditions_list = json.loads(self.conditions.replace("'", '"'))
        return conditions_list

    def _get_event_by_name(self, interface):
        """
        interface: is string of a list of dictionary containing id, name, type, inputs and outputs
        """
        interface = json.loads(interface.replace("'", '"'))
        for i in interface:
            if i.get('name') == self.event_name and i['type'] == 'event':
                return i
        return {}

    class Meta:
        ordering = ('created',)
