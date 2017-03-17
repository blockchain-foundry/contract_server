# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oracles', '0003_subcontract'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('source_code', models.TextField()),
                ('color', models.PositiveIntegerField()),
                ('amount', models.PositiveIntegerField()),
                ('interface', models.TextField(default='')),
                ('contract_address', models.CharField(max_length=100, default='', blank=True)),
            ],
            options={
                'ordering': ('created',),
            },
        ),
        migrations.CreateModel(
            name='MultisigAddress',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('address', models.CharField(max_length=100, default='', blank=True)),
                ('script', models.CharField(max_length=4096, default='', blank=True)),
                ('least_sign_number', models.PositiveIntegerField(default=1)),
                ('oracles', models.ManyToManyField(to='oracles.Oracle')),
            ],
            options={
                'ordering': ('created',),
            },
        ),
        migrations.AddField(
            model_name='contract',
            name='multisig_address',
            field=models.ForeignKey(to='contracts.MultisigAddress'),
        ),
    ]
