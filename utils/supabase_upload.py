from django.conf import settings
from supabase import create_client, Client


def upload_user_avatar(file, user_id, file_name=None, content_type='image/jpeg'):
    """
    Uploads an avatar to Supabase Storage
    :param file: File object or BytesIO buffer
    :param user_id: User ID for path
    :param file_name: Optional custom file name
    :param content_type: MIME type of the file
    :return: Public URL or None
    """
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    bucket_name = settings.SUPABASE_BUCKET

    # Generate file path
    if file_name:
        file_path = f"avatars/{user_id}/{file_name}"
    elif hasattr(file, 'name'):
        file_path = f"avatars/{user_id}/{file.name}"
    else:
        file_path = f"avatars/{user_id}/avatar_{user_id}.png"

    try:
        # Prepare file data
        if hasattr(file, 'read'):
            file_data = file.read()
        else:
            file_data = file

        # Upload file
        upload_response = supabase.storage.from_(bucket_name).upload(
            file_path,
            file_data,
            file_options={"content-type": content_type}
        )

        # Check for errors
        if upload_response.error:
            print(f"Supabase upload error: {upload_response.error.message}")
            return None

        # Get public URL
        url_response = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return url_response

    except Exception as e:
        print(f"Error uploading avatar: {str(e)}")
        return None