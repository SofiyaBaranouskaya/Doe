# apps/users/migrations/0016_add_token_field_null.py
from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0015_challenge_poster_base64_challenge_poster_url_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='token',
            field=models.UUIDField(default=uuid.uuid4, null=True),
        ),
    ]