# Generated by Django 4.2.3 on 2024-02-22 15:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0038_room_archived'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='room',
            name='archived',
        ),
    ]
