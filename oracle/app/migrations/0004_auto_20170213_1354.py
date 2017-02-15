# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_auto_20170209_0518'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registration',
            name='proposal',
        ),
        migrations.DeleteModel(
            name='Registration',
        ),
    ]
