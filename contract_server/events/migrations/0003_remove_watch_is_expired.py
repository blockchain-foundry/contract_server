# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_auto_20170104_1649'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='watch',
            name='is_expired',
        ),
    ]
