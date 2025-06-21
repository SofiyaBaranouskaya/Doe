# storage_backends.py

from storages.backends.s3boto3 import S3Boto3Storage

class StorjVideoStorage(S3Boto3Storage):
    bucket_name = 'videos'  # Имя твоего бакета в Storj
    location = ''
    default_acl = 'public-read'
    custom_domain = False
