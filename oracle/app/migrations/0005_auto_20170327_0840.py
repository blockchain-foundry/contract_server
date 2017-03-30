# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_auto_20170213_1354'),
    ]

    operations = [
        migrations.RenameField(
            model_name='proposal',
            old_name='multisig_addr',
            new_name='multisig_address',
        ),
    ]
