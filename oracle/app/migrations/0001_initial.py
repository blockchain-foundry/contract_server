# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Proposal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('source_code', models.TextField()),
                ('public_key', models.CharField(max_length=100)),
                ('multisig_addr', models.CharField(blank=True, max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('address', models.CharField(max_length=100)),
            ],
            options={
                'ordering': ('public_key',),
            },
        ),
        migrations.CreateModel(
            name='Registration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('registrated', models.DateTimeField(auto_now_add=True)),
                ('multisig_address', models.CharField(max_length=100)),
                ('redeem_script', models.CharField(max_length=256)),
                ('proposal', models.OneToOneField(to='app.Proposal')),
            ],
            options={
                'ordering': ('registrated',),
            },
        ),
    ]
