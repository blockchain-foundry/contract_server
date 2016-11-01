from django.db import models


class Contract(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    source_code = models.TextField()
    color_id = models.PositiveIntegerField()
    amount = models.PositiveIntegerField()
    multisig_address = models.CharField(max_length=100, blank=True, default='')
    multisig_script = models.CharField(max_length=4096, blank=True, default='')
    interface = models.TextField(default='')
    oracles = models.ManyToManyField('Oracle')
    class Meta:
        ordering = ('created',)

class Oracle(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    url = models.URLField()
    class Meta:
        ordering = ('created',)

