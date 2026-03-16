# aichat/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class ChatSession(models.Model):
    """
    Модель для хранения сессии чата.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,  # Разрешаем анонимные сессии
        blank=True
    )
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=200, blank=True, default='New Chat')
    context = models.JSONField(default=dict, blank=True)  # Хранит контекст (тема, уровень и т.д.)
    model_used = models.CharField(max_length=100, default='-')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Chat session'
        verbose_name_plural = 'Chat session'

    def __str__(self):
        return f"{self.title} ({self.session_id})"

    def get_message_count(self):
        return self.messages.count()


class ChatMessage(models.Model):
    """
    Модель для хранения сообщений в чате.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'Sistem'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    tokens_used = models.IntegerField(default=0, help_text="Tokens needed")
    metadata = models.JSONField(default=dict, blank=True)  # Доп. информация (модель, температура и т.д.)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Messages'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."

    def save(self, *args, **kwargs):
        # Автоматически обновляем updated_at родительской сессии
        super().save(*args, **kwargs)
        self.session.save()  # Триггерит обновление updated_at


class UserFeedback(models.Model):
    """
    Модель для хранения обратной связи пользователя об ответах AI.
    """
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    message = models.OneToOneField(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'

    def __str__(self):
        return f"Rate {self.rating} for message #{self.message_id}"