# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0003_auto_20170610_1306'),
    ]

    operations = [
        migrations.AlterField(
            model_name='multisigaddress',
            name='address',
            field=models.CharField(unique=True, max_length=100, blank=True),
        ),
    ]
