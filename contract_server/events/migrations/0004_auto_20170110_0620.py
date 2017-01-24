# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.utils.timezone import utc
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_remove_watch_is_expired'),
    ]

    operations = [
        migrations.AlterField(
            model_name='watch',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2017, 1, 10, 6, 20, 28, 444683, tzinfo=utc)),
        ),
    ]
