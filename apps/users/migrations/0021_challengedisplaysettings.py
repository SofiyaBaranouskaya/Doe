# Generated by Django 5.1.6 on 2025-04-11 07:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_remove_challenge_block_display_fields_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChallengeDisplaySettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_type', models.CharField(choices=[('text', 'Text Blocks'), ('table', 'Table')], default='text', max_length=10, verbose_name='Display type')),
                ('fields_to_show', models.JSONField(blank=True, null=True, verbose_name='Fields to display (order matters)')),
                ('auto_adjust_table', models.BooleanField(default=True, verbose_name='Auto adjust rows/columns')),
                ('num_columns', models.PositiveIntegerField(blank=True, null=True, verbose_name='Number of columns (if not auto)')),
                ('num_rows', models.PositiveIntegerField(blank=True, null=True, verbose_name='Number of rows (if not auto)')),
                ('column_titles', models.JSONField(blank=True, null=True, verbose_name='Column titles (list of strings)')),
                ('row_titles', models.JSONField(blank=True, null=True, verbose_name='Row titles (optional)')),
                ('field_mapping', models.JSONField(blank=True, null=True, verbose_name='Mapping fields to table cells')),
                ('row_color_rules', models.JSONField(blank=True, null=True, verbose_name='Row coloring rules (based on answer values)')),
                ('challenge', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='display_settings', to='users.challenge')),
            ],
            options={
                'verbose_name': 'Challenge Display Settings',
                'verbose_name_plural': 'Challenge Display Settings',
            },
        ),
    ]
