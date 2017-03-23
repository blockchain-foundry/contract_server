# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0001_initial'),
        ('events', '0003_rename_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='watch',
            name='multisig_contract',
        ),
        migrations.RemoveField(
            model_name='watch',
            name='subcontract',
        ),
        migrations.AddField(
            model_name='watch',
            name='contract',
            field=models.ForeignKey(blank=True, to='contracts.Contract', null=True, related_name='watch'),
        ),
    ]
