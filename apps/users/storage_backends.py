from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

class StorjVideoStorage(S3Boto3Storage):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME  # bucket1
    custom_domain = False  # чтобы не использовать стандартный domain S3

    def url(self, name, parameters=None, expire=None, http_method=None):
        filename = name.split('/')[-1]
        return f"https://link.storjshare.io/s/jx75pxv4u7pempj4wj4hum3wqhaq/bucket1/{filename}"
