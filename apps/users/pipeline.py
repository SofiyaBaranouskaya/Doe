import requests
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages
from social_core.exceptions import AuthAlreadyAssociated

User = get_user_model()


def create_custom_user(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        return {'user': user}  # Уже есть — ничего не делаем

    email = details.get('email')
    if not email:
        return

    # Защита от дубликатов по email
    UserModel = get_user_model()
    try:
        existing_user = UserModel.objects.get(email=email)
        return {'user': existing_user}
    except UserModel.DoesNotExist:
        pass

    username = details.get('username') or email.split('@')[0]

    # Создаём пользователя
    new_user = UserModel.objects.create_user(
        username=username,
        email=email,
        first_name=details.get('first_name', ''),
        last_name=details.get('last_name', ''),
        is_active=True,
        level='Trailblazer'  # По умолчанию Trailblazer
    )

    # Сохраняем аватар
    if backend.name == 'google-oauth2':
        response = kwargs.get('response', {})
        picture_url = response.get('picture')
        if picture_url:
            try:
                img_response = requests.get(picture_url)
                if img_response.status_code == 200:
                    filename = f'{slugify(new_user.username)}_google.jpg'
                    new_user.profile_picture.save(
                        filename,
                        ContentFile(img_response.content),
                        save=True
                    )
            except Exception as e:
                print(f"Error downloading profile picture: {e}")

    strategy.session_set('is_new_user', True)  # полезно, если есть логика на фронте

    return {
        'user': new_user,
        'is_new': True
    }



def associate_by_email(backend, user, response, strategy, *args, **kwargs):
    email = response.get('email')
    if not email:
        return

    try:
        existing_user = get_user_model().objects.get(email=email)
        if existing_user != user:
            strategy.session_set('is_new_user', False)  # вход
            return {'user': existing_user}
    except get_user_model().DoesNotExist:
        strategy.session_set('is_new_user', True)  # регистрация
        pass
