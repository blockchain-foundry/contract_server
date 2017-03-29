# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='hash_op_return',
            field=models.IntegerField(default=-1),
        ),
        migrations.AddField(
            model_name='contract',
            name='is_deployed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='contract',
            name='sender_evm_address',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='contract',
            name='sender_nonce_predicted',
            field=models.IntegerField(default=-1),
        ),
        migrations.AddField(
            model_name='contract',
            name='tx_hash_init',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
