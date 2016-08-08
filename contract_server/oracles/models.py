from django.db import models
from django.core.validators import URLValidator

class Oracle(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    url = models.TextField(validators=[URLValidator()])

    class Meta:
        ordering = ('created',)
