# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Keystore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=100)),
                ('private_key', models.CharField(max_length=100)),
                ('contract_address', models.CharField(max_length=100)),
                ('sender_address', models.CharField(max_length=100)),
                ('url', models.CharField(max_length=100)),
            ],
        ),
    ]
