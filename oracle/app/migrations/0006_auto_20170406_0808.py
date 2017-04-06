# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_auto_20170327_0840'),
    ]

    operations = [
        migrations.AlterField(
            model_name='keystore',
            name='public_key',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='public_key',
            field=models.CharField(max_length=200),
        ),
    ]
