# Generated by Django 5.1.6 on 2025-04-22 07:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0036_schools'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schools',
            name='name',
            field=models.CharField(max_length=70),
        ),
    ]
