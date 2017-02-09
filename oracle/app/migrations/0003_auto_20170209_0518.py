# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_keystore'),
    ]

    operations = [
        migrations.CreateModel(
            name='OraclizeContract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=100)),
                ('interface', models.TextField()),
                ('byte_code', models.TextField()),
            ],
            options={
                'ordering': ('address',),
            },
        ),
        migrations.CreateModel(
            name='ProposalOraclizeLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('receiver', models.CharField(max_length=100)),
                ('color', models.CharField(max_length=100)),
                ('oraclize_contract', models.ForeignKey(to='app.OraclizeContract')),
            ],
            options={
                'ordering': ('color',),
            },
        ),
        migrations.AddField(
            model_name='proposal',
            name='links',
            field=models.ManyToManyField(to='app.ProposalOraclizeLink'),
        ),
    ]
