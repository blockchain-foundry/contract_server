# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0005_auto_20170111_0410'),
    ]

    operations = [
        migrations.AddField(
            model_name='watch',
            name='subscription_id',
            field=models.CharField(max_length=100, default=datetime.datetime(2017, 1, 18, 2, 6, 59, 427007, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='watch',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2017, 1, 18, 2, 6, 34, 517288, tzinfo=utc)),
        ),
    ]
