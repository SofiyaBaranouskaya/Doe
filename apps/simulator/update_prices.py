"""
python manage.py update_prices

Обновить котировки всех активов из Yahoo Finance.
Можно запускать по крону каждые 15 минут в часы работы рынка.

Crontab пример:
    */15 9-23 * * 1-5 /path/to/venv/bin/python /path/to/manage.py update_prices
"""
from django.core.management.base import BaseCommand
from services import PriceFetcher


class Command(BaseCommand):
    help = 'Обновить котировки всех активов из Yahoo Finance'

    def handle(self, *args, **options):
        self.stdout.write('Загружаем котировки...')
        fetcher = PriceFetcher()
        fetcher.update_all_prices()
        self.stdout.write(self.style.SUCCESS('Котировки обновлены!'))
