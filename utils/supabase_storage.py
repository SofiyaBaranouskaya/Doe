import os
import mimetypes
import requests
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.conf import settings


class SupabaseStorage(Storage):
    def __init__(self):
        self.base_url = settings.SUPABASE_URL  # Избегаем конфликта имен
        self.key = settings.SUPABASE_KEY
        self.bucket = settings.SUPABASE_BUCKET
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }

    def _get_full_path(self, name):
        return f"{self.bucket}/{name}"

    def _save(self, name, content):
        upload_url = f"{self.base_url}/storage/v1/object/{self._get_full_path(name)}"
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        response = requests.put(
            upload_url,
            data=content.read(),
            headers={**self.headers, "Content-Type": content_type},
        )

        if not response.ok:
            raise Exception(f"Upload failed: {response.status_code}\n{response.text}")
        return name

    def url(self, name):
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{name}"

    def exists(self, name):
        url = f"{self.base_url}/storage/v1/object/info/{self.bucket}/{name}"
        return requests.get(url, headers=self.headers).status_code == 200

    def delete(self, name):
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{name}"
        return requests.delete(url, headers=self.headers).ok