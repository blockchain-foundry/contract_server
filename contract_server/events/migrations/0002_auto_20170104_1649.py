# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Watch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('multisig_address', models.CharField(blank=True, max_length=100, default='')),
                ('key', models.TextField()),
                ('is_expired', models.BooleanField()),
            ],
            options={
                'ordering': ('created',),
            },
        ),
        migrations.RemoveField(
            model_name='event',
            name='is_expired',
        ),
        migrations.RemoveField(
            model_name='event',
            name='storage_after',
        ),
        migrations.RemoveField(
            model_name='event',
            name='storage_before',
        ),
    ]
