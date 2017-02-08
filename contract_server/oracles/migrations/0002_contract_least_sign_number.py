# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oracles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='least_sign_number',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
