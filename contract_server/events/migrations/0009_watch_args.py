# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0008_auto_20170118_0216'),
    ]

    operations = [
        migrations.AddField(
            model_name='watch',
            name='args',
            field=models.CharField(max_length=1000, default='', blank=True),
        ),
    ]
