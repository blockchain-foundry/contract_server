# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('evm_manager', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContractInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('multisig_address', models.CharField(max_length=100)),
                ('contract_address', models.CharField(max_length=100)),
                ('state_info', models.ForeignKey(to='evm_manager.StateInfo')),
            ],
        ),
    ]
