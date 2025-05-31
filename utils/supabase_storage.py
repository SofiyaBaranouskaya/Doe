from django.core.files.storage import Storage
from supabase import create_client
from django.conf import settings
import uuid
import time

class SupabaseStorage(Storage):
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name
        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    def _save(self, name, content):
        data = content.read()
        name = self.get_available_name(name)

        response = self.client.storage.from_(self.bucket_name).upload(
            name,
            data,
            {"content-type": content.content_type}
        )

        # Проверяем статус ответа
        if hasattr(response, 'status_code') and response.status_code >= 400:
            raise Exception(f"Upload failed with status code {response.status_code}")

        # Если response.data или response.get('error') существуют, можно добавить дополнительные проверки
        # Например:
        # if hasattr(response, 'data') and response.data is None:
        #     raise Exception("Upload failed: no data returned")

        return name

    def url(self, name):
        return self.client.storage.from_(self.bucket_name).get_public_url(name)

    def exists(self, name):
        # Проверяем наличие файла в Supabase
        try:
            response = self.client.storage.from_(self.bucket_name).list()
            if response.error:
                print(f"⚠️ Supabase list error: {response.error.message}")
                return False
            return any(obj['name'] == name for obj in response.data)
        except Exception as e:
            print(f"⚠️ Exists check failed: {e}")
            return False

    def get_available_name(self, name, max_length=None):
        # Генерируем уникальное имя файла
        ext = name.split('.')[-1]
        return f"{uuid.uuid4().hex}.{ext}"

    def deconstruct(self):
        return (
            'utils.supabase_storage.SupabaseStorage',
            [],
            {'bucket_name': self.bucket_name},
        )
