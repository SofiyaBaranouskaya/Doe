from django.conf import settings
from supabase import create_client, Client


def upload_user_avatar(file, user_id, bucket_name, file_name=None, content_type='image/jpeg'):
    """
    Uploads an avatar to Supabase Storage.
    :param file: File object or BytesIO buffer
    :param user_id: User ID for organizing storage paths
    :param bucket_name: Supabase Storage bucket name
    :param file_name: Optional file name
    :param content_type: MIME type
    :return: Relative path or None if failed
    """
    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception:
        return None

    if file_name:
        file_path = f"avatars/{user_id}/{file_name}"
    elif hasattr(file, 'name'):
        file_path = f"avatars/{user_id}/{file.name}"
    else:
        file_path = f"avatars/{user_id}/avatar_{user_id}.png"

    try:
        if hasattr(file, 'read'):
            file.seek(0)
            file_data = file.read()
        else:
            file_data = file

        upload_response = supabase.storage.from_(bucket_name).upload(
            file_path,
            file_data,
            file_options={"content-type": content_type, "x-upsert": "true"}
        )

        if not (upload_response and hasattr(upload_response, 'path')):
            return None

        # Optionally check access via get_public_url (optional in prod)
        supabase.storage.from_(bucket_name).get_public_url(file_path)

        return file_path

    except Exception:
        return None
