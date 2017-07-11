# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0002_auto_20170328_0856'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contract',
            name='multisig_address',
        ),
        migrations.RemoveField(
            model_name='contract',
            name='sender_nonce_predicted',
        ),
        migrations.AddField(
            model_name='contract',
            name='contract_multisig_address',
            field=models.ForeignKey(blank=True, related_name='contract', null=True, to='contracts.MultisigAddress'),
        ),
        migrations.AddField(
            model_name='contract',
            name='state_multisig_address',
            field=models.ForeignKey(related_name='contract_set', null=True, to='contracts.MultisigAddress'),
        ),
        migrations.AddField(
            model_name='multisigaddress',
            name='is_state_multisig',
            field=models.BooleanField(default=False),
        ),
    ]
