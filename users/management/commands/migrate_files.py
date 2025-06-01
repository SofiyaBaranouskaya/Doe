from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files import File
import os


class Command(BaseCommand):
    help = 'Migrate profile pictures to Supabase'

    def handle(self, *args, **options):
        User = get_user_model()

        for user in User.objects.exclude(profile_picture=''):
            if user.profile_picture:
                try:
                    temp_path = f'/tmp/{user.profile_picture.name}'

                    with open(temp_path, 'wb') as f:
                        for chunk in user.profile_picture.chunks():
                            f.write(chunk)

                    with open(temp_path, 'rb') as f:
                        user.profile_picture.save(user.profile_picture.name, File(f))

                    self.stdout.write(f"Success: {user.username}")
                    os.remove(temp_path)
                except Exception as e:
                    self.stderr.write(f"Error for {user.username}: {str(e)}")