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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('created', models.DateTimeField(default=events.models.default_time)),
                ('multisig_address', models.CharField(max_length=100)),
                ('key', models.CharField(max_length=200)),
                ('subscription_id', models.CharField(max_length=100)),
                ('args', models.CharField(default='', max_length=1000, blank=True)),
                ('is_closed', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('created',),
            },
        ),
    ]
