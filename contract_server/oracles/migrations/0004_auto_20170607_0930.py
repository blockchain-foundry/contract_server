# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oracles', '0003_subcontract'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contract',
            name='oracles',
        ),
        migrations.RemoveField(
            model_name='subcontract',
            name='parent_contract',
        ),
        migrations.DeleteModel(
            name='Contract',
        ),
        migrations.DeleteModel(
            name='SubContract',
        ),
    ]
