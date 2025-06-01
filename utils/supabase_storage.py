import os
import mimetypes
import requests
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.conf import settings

class SupabaseStorage(Storage):
    def __init__(self):
        self.base_url = settings.SUPABASE_URL  # ✅ renamed to avoid conflict
        self.key = settings.SUPABASE_KEY
        self.bucket = settings.SUPABASE_BUCKET
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }

    def _get_full_path(self, name):
        return f"{self.bucket}/{name}"

    def _save(self, name, content):
        file_path = self._get_full_path(name)
        upload_url = f"{self.base_url}/storage/v1/object/{file_path}"  # ✅ changed

        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        response = requests.put(
            upload_url,
            data=content.read(),
            headers={
                **self.headers,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )

        if not response.ok:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")

        return name

    def _open(self, name, mode='rb'):
        file_url = f"{self.base_url}/storage/v1/object/{self.bucket}/{name}"  # ✅ changed
        response = requests.get(file_url, headers=self.headers)
        if not response.ok:
            raise Exception(f"Download failed: {response.status_code} - {response.text}")
        return ContentFile(response.content)

    def url(self, name):
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{name}"  # ✅ changed

    def exists(self, name):
        check_url = f"{self.base_url}/storage/v1/object/info/{self.bucket}/{name}"  # ✅ changed
        response = requests.get(check_url, headers=self.headers)
        return response.status_code == 200

    def delete(self, name):
        delete_url = f"{self.base_url}/storage/v1/object/{self.bucket}/{name}"  # ✅ changed
        response = requests.delete(delete_url, headers=self.headers)
        return response.ok
