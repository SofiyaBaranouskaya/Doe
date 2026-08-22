# apps/users/migrations/0017_populate_token_values.py
from django.db import migrations
import uuid

def gen_uuid(apps, schema_editor):
    Invitation = apps.get_model('users', 'Invitation')
    for invitation in Invitation.objects.all():
        invitation.token = uuid.uuid4()
        invitation.save(update_fields=['token'])

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0016_add_token_field_null'),
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]