# apps/users/exceptions.py
from social_core.exceptions import AuthAlreadyAssociated
from django.shortcuts import redirect
from django.contrib import messages


def social_auth_exception_handler(request, exception):
    # Проверяем, является ли ошибка AuthAlreadyAssociated
    if isinstance(exception, AuthAlreadyAssociated):
        email = request.GET.get('email')

        if email:
            messages.info(request, f"Этот email ({email}) уже используется другим аккаунтом. Пожалуйста, войдите с паролем.")
            return redirect('login')  # Перенаправить на страницу логина

    # Если ошибка не связана с AuthAlreadyAssociated, пробуем стандартный обработчик
    return None
