# Generated by Django 4.2.3 on 2023-08-28 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0030_remove_message_replying'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='replying',
            field=models.BooleanField(default=False),
        ),
    ]
