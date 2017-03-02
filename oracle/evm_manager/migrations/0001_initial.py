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
                ('multisig_address', models.CharField(primary_key=True, max_length=100, serialize=False)),
                ('latest_tx_time', models.CharField(blank=True, default='', max_length=100)),
                ('latest_tx_hash', models.CharField(blank=True, default='', max_length=100)),
            ],
        ),
    ]
