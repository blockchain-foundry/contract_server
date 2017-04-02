# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_auto_20170323_1754'),
    ]

    operations = [
        migrations.AddField(
            model_name='watch',
            name='conditions',
            field=models.CharField(default='', blank=True, max_length=5000),
        ),
    ]
