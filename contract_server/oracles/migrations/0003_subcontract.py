# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oracles', '0002_contract_least_sign_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubContract',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('deploy_address', models.CharField(default='', max_length=100, blank=True)),
                ('source_code', models.TextField()),
                ('color_id', models.PositiveIntegerField()),
                ('amount', models.PositiveIntegerField()),
                ('interface', models.TextField(default='')),
                ('parent_contract', models.ForeignKey(related_name='subcontract', to='oracles.Contract')),
            ],
        ),
    ]
