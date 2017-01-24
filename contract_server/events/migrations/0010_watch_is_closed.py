# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0009_watch_args'),
    ]

    operations = [
        migrations.AddField(
            model_name='watch',
            name='is_closed',
            field=models.BooleanField(default=False),
        ),
    ]
