# Generated by Django 4.2.3 on 2023-09-23 11:55

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0009_alter_room_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='status',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='status_del_at',
            field=models.DateField(blank=True, default=datetime.date.today, verbose_name='delete_status_at'),
        ),
        migrations.AlterField(
            model_name='room',
            name='name',
            field=models.CharField(max_length=200),
        ),
    ]
