# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import events.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Watch',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('created', models.DateTimeField(default=events.models.default_time)),
                ('multisig_address', models.CharField(max_length=100)),
                ('key', models.CharField(max_length=200)),
                ('subscription_id', models.CharField(max_length=100)),
                ('args', models.CharField(blank=True, max_length=1000, default='')),
                ('is_closed', models.BooleanField(default=False)),
                ('receiver_address', models.CharField(max_length=100)),
            ],
            options={
                'ordering': ('created',),
            },
        ),
    ]
