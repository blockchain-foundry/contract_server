# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('source_code', models.TextField()),
                ('color_id', models.PositiveIntegerField()),
                ('amount', models.PositiveIntegerField()),
                ('multisig_address', models.CharField(default='', max_length=100, blank=True)),
                ('multisig_script', models.CharField(default='', max_length=4096, blank=True)),
                ('interface', models.TextField(default='')),
            ],
            options={
                'ordering': ('created',),
            },
        ),
        migrations.CreateModel(
            name='Oracle',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(default='', max_length=100, blank=True)),
                ('url', models.URLField()),
            ],
            options={
                'ordering': ('created',),
            },
        ),
        migrations.AddField(
            model_name='contract',
            name='oracles',
            field=models.ManyToManyField(to='oracles.Oracle'),
        ),
    ]
