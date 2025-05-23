# Generated by Django 5.1.6 on 2025-04-11 07:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_alter_challengedisplaysettings_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tablecolumnsetting',
            name='custom_values',
            field=models.TextField(blank=True, verbose_name='Custom values (comma-separated)'),
        ),
        migrations.AddField(
            model_name='tablecolumnsetting',
            name='use_field',
            field=models.CharField(choices=[('element', 'From element'), ('custom', 'Custom values')], default='element', max_length=10, verbose_name='Data source'),
        ),
        migrations.AlterField(
            model_name='tablecolumnsetting',
            name='element',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.challengeelement', verbose_name='Field (if from element)'),
        ),
    ]
