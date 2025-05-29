from django.conf import settings
from supabase import create_client, Client


def upload_user_avatar(file, user_id):
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    bucket_name = settings.SUPABASE_BUCKET
    file_path = f"avatars/{user_id}/{file.name}"

    try:
        # Загрузка файла
        upload_response = supabase.storage.from_(bucket_name).upload(
            file_path,
            file.read(),
            file_options={"content-type": file.content_type}
        )

        # Проверка на ошибки
        if upload_response.error:
            print(f"Supabase upload error: {upload_response.error.message}")
            return None

        # Получение публичного URL
        url_response = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return url_response

    except Exception as e:
        print(f"Error uploading avatar: {str(e)}")
        return None