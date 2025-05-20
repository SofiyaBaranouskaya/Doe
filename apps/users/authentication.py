from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
import re

class EmailOrPhoneAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Проверяем, что введено: email или телефон
        if username:
            try:
                if re.match(r"[^@]+@[^@]+\.[^@]+", username):  # Это email
                    user = get_user_model().objects.get(email=username)
                else:
                    user = get_user_model().objects.get(phone_number=username)
            except ObjectDoesNotExist:
                return None

            if user.check_password(password):
                return user
        return None
