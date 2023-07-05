# Generated by Django 4.1.3 on 2023-07-05 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_alter_user_avatar'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='room',
            options={'ordering': ['-pinned', '-updated', '-created']},
        ),
        migrations.AddField(
            model_name='room',
            name='pinned',
            field=models.BooleanField(default=False),
        ),
    ]
