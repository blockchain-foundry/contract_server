# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StateInfo',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('multisig_address', models.CharField(max_length=100, serialize=False, primary_key=True)),
                ('latest_tx_time', models.CharField(default='', max_length=100, blank=True)),
                ('latest_tx_hash', models.CharField(default='', max_length=100, blank=True)),
            ],
        ),
    ]
