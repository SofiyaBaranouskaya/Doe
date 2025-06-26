from celery import shared_task
from .models import ChallengeUserAnswer
import time

@shared_task
def process_uploaded_file(file_id):
    try:
        answer = ChallengeUserAnswer.objects.get(id=file_id)

        # Тут можно обрабатывать файл: извлекать метаданные, конвертировать, отправлять куда-то и т.д.
        print(f"Начинаем обработку файла: {answer.file.name}")
        time.sleep(5)  # имитация долгой задачи
        print(f"Файл {answer.file.name} успешно обработан")
    except ChallengeUserAnswer.DoesNotExist:
        print(f"Файл с id {file_id} не найден")
