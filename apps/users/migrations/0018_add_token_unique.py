# apps/users/migrations/0018_add_token_unique.py
from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0017_populate_token_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invitation',
            name='token',
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]