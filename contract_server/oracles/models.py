from django.db import models


class Oracle(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    url = models.URLField()

    class Meta:
        ordering = ('created',)
