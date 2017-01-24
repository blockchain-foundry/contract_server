# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0010_watch_is_closed'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Event',
        ),
        migrations.AlterField(
            model_name='watch',
            name='key',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='watch',
            name='multisig_address',
            field=models.CharField(max_length=100),
        ),
    ]
