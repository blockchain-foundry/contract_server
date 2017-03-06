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
    least_sign_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('created',)


class SubContract(models.Model):
    parent_contract = models.ForeignKey(Contract, related_name='subcontract')
    deploy_address = models.CharField(max_length=100, blank=True, default='')
    source_code = models.TextField()
    color_id = models.PositiveIntegerField()
    amount = models.PositiveIntegerField()
    interface = models.TextField(default='')


class Oracle(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    url = models.URLField()

    class Meta:
        ordering = ('created',)
