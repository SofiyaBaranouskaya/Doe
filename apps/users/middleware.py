# apps/users/middleware.py
from django.utils import timezone
from datetime import timedelta
from .metrics import active_users  # Убираем несуществующие импорты
import time


class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Время начала запроса
        start_time = time.time()

        # Обработка запроса
        response = self.get_response(request)

        # Время выполнения
        duration = time.time() - start_time

        # Просто логируем для отладки (пока нет метрик)
        print(f"Request to {request.path} took {duration:.2f} seconds")

        return response