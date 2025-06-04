# utils/supabase_storage.py
import os
import mimetypes
import requests
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.conf import settings
from environ import ImproperlyConfigured
from django.utils.deconstruct import deconstructible

@deconstructible
class SupabaseStorage(Storage):
    def __init__(self, bucket_name):
        if not bucket_name:
            raise ImproperlyConfigured("SupabaseStorage requires 'bucket_name' parameter.")

        self.bucket = bucket_name
        self.base_url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY

        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }

    def _get_full_path(self, name):
        return f"{self.bucket}/{name}"

    def _save(self, name, content):
        file_path = self._get_full_path(name)
        upload_url = f"{self.base_url}/storage/v1/object/{file_path}"
        print(f"Trying to save to bucket: {self.bucket}")

        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        # Перемотка файла перед чтением
        if hasattr(content, 'seekable') and content.seekable():
            content.seek(0)

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
            error_msg = f"Upload failed: {response.status_code} - {response.text}"
            print(error_msg)
            raise Exception(error_msg)

        return name

    def _open(self, name, mode='rb'):
        from django.core.files.base import ContentFile
        download_url = f"{self.base_url}/storage/v1/object/{self.bucket}/{name}"
        response = requests.get(download_url, headers=self.headers)
        if response.ok:
            return ContentFile(response.content)
        raise IOError(f"Unable to open file: {name}")


    def url(self, name):
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{name}"

    def exists(self, name):
        check_url = f"{self.base_url}/storage/v1/object/info/{self.bucket}/{name}"
        response = requests.get(check_url, headers=self.headers)
        return response.status_code == 200

    def delete(self, name):
        delete_url = f"{self.base_url}/storage/v1/object/{self.bucket}/{name}"
        response = requests.delete(delete_url, headers=self.headers)
        return response.ok