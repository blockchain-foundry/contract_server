# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.utils.timezone import utc
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0006_auto_20170118_0206'),
    ]

    operations = [
        migrations.AlterField(
            model_name='watch',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2017, 1, 18, 2, 7, 2, 773811, tzinfo=utc)),
        ),
    ]
