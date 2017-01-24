# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('multisig_address', models.CharField(blank=True, default='', max_length=100)),
                ('key', models.TextField()),
                ('storage_before', models.TextField(blank=True, default='')),
                ('storage_after', models.TextField(blank=True, default='')),
                ('is_expired', models.BooleanField()),
            ],
            options={
                'ordering': ('created',),
            },
        ),
    ]
