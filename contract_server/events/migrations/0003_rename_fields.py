# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_watch_receiver_address'),
        ('oracles', '0003_subcontract'),
    ]

    operations = [
        migrations.RenameField(
            model_name='watch',
            old_name='key',
            new_name='event_name',
        ),
        migrations.RemoveField(
            model_name='watch',
            name='subscription_id',
        ),
        migrations.RemoveField(
            model_name='watch',
            name='multisig_address',
        ),
        migrations.RemoveField(
            model_name='watch',
            name='receiver_address',
        ),
        migrations.AddField(
            model_name='watch',
            name='multisig_contract',
            field=models.ForeignKey(related_name='watch', null=True, blank=True, to='oracles.Contract'),
        ),
        migrations.AddField(
            model_name='watch',
            name='subcontract',
            field=models.ForeignKey(related_name='watch', null=True, blank=True, to='oracles.SubContract'),
        ),
        migrations.AlterField(
            model_name='watch',
            name='args',
            field=models.CharField(max_length=5000, blank=True, default=''),
        ),
    ]
