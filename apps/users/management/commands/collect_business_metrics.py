# apps/users/management/commands/collect_business_metrics.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.users.models import User, Content
from django.db.models import Count, Avg
from apps.users.metrics import active_users  # Правильный импорт


class Command(BaseCommand):
    help = 'Collect business metrics for Prometheus'

    def handle(self, *args, **options):
        # Активные пользователи
        now = timezone.now()

        # Daily active users (за последние 24 часа)
        daily_active = User.objects.filter(
            last_login__gte=now - timedelta(days=1)
        ).count()

        # Weekly active users (за последние 7 дней)
        weekly_active = User.objects.filter(
            last_login__gte=now - timedelta(days=7)
        ).count()

        # Monthly active users (за последние 30 дней)
        monthly_active = User.objects.filter(
            last_login__gte=now - timedelta(days=30)
        ).count()

        # Активные пользователи по периодам
        active_users.labels(period='daily').set(daily_active)
        active_users.labels(period='weekly').set(weekly_active)
        active_users.labels(period='monthly').set(monthly_active)

        self.stdout.write(
            self.style.SUCCESS(f'Metrics collected: Daily={daily_active}, Weekly={weekly_active}, Monthly={monthly_active}')
        )