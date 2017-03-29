from django.db import models


# class Oracle(models.Model):
#   created = models.DateTimeField(auto_now_add=True)
#   name = models.CharField(max_length=100, blank=True, default='')
#   url = models.TextField(validators=[URLValidator()])

#   class Meta:
#       ordering = ('created',)

class Keystore(models.Model):
    public_key = models.CharField(max_length=100)
    private_key = models.CharField(max_length=100)


class OraclizeContract(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    interface = models.TextField()
    byte_code = models.TextField()

    class Meta:
        ordering = ('address',)


class ProposalOraclizeLink(models.Model):
    receiver = models.CharField(max_length=100)
    color = models.CharField(max_length=100)
    oraclize_contract = models.ForeignKey(OraclizeContract)

    class Meta:
        ordering = ('color',)


class Proposal(models.Model):
    source_code = models.TextField()
    public_key = models.CharField(max_length=100)
    multisig_address = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    address = models.CharField(max_length=100)
    links = models.ManyToManyField(ProposalOraclizeLink)

    class Meta:
        ordering = ('public_key',)
