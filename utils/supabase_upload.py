import uuid
from supabase import create_client
from django.conf import settings

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def upload_user_avatar(file, user_id, is_file_like=False):
    ext = 'png'  # или jpg, если нужно
    filename = f"profile_pictures/{user_id}_{uuid.uuid4()}.{ext}"

    if not is_file_like:
        file_content = file.read()
    else:
        file.seek(0)
        file_content = file.read()

    # Загружаем в Supabase
    res = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(filename, file_content, {"content-type": "image/png"})
    if res.get("error"):
        raise Exception(res["error"]["message"])

    return supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(filename)

