# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import events.models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_auto_20170110_0620'),
    ]

    operations = [
        migrations.AlterField(
            model_name='watch',
            name='created',
            field=models.DateTimeField(default=events.models.default_time),
        ),
    ]
