# Generated by Django 5.1.6 on 2025-04-22 07:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0035_user_cities_user_current_focus_user_date_of_birth_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Schools',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=70, null=True)),
                ('code', models.IntegerField(default=0)),
            ],
        ),
    ]
