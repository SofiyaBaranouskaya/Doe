"""python manage.py seed_assets"""
from django.core.management.base import BaseCommand
from models import Asset

ASSETS = [
    {'ticker': 'AAPL',  'name': 'Apple Inc.',                  'asset_type': 'stock',     'description': 'Крупнейшая технологическая компания мира. Производитель iPhone, Mac, iPad.'},
    {'ticker': 'TSLA',  'name': 'Tesla Inc.',                  'asset_type': 'stock',     'description': 'Лидер рынка электромобилей и систем накопления энергии.'},
    {'ticker': 'GOOGL', 'name': 'Alphabet (Google)',           'asset_type': 'stock',     'description': 'Материнская компания Google, YouTube и других сервисов.'},
    {'ticker': 'AMZN',  'name': 'Amazon.com Inc.',             'asset_type': 'stock',     'description': 'Крупнейший в мире маркетплейс и облачный провайдер AWS.'},
    {'ticker': 'MSFT',  'name': 'Microsoft Corp.',             'asset_type': 'stock',     'description': 'Производитель Windows, Office, Azure. Лидер ИИ-рынка.'},
    {'ticker': 'NVDA',  'name': 'NVIDIA Corp.',                'asset_type': 'stock',     'description': 'Производитель GPU. Ключевой поставщик чипов для ИИ.'},
    {'ticker': 'META',  'name': 'Meta Platforms',              'asset_type': 'stock',     'description': 'Facebook, Instagram, WhatsApp.'},
    {'ticker': 'JPM',   'name': 'JPMorgan Chase',              'asset_type': 'stock',     'description': 'Крупнейший банк США.'},
    {'ticker': 'SPY',   'name': 'SPDR S&P 500 ETF',           'asset_type': 'etf',       'description': 'Отслеживает индекс S&P 500 — 500 крупнейших компаний США.'},
    {'ticker': 'QQQ',   'name': 'Invesco QQQ (NASDAQ)',        'asset_type': 'etf',       'description': 'NASDAQ-100 — 100 крупнейших нефинансовых компаний.'},
    {'ticker': 'VTI',   'name': 'Vanguard Total Stock Market', 'asset_type': 'etf',       'description': 'Весь рынок акций США (~3500 компаний).'},
    {'ticker': 'TLT',   'name': 'iShares 20+ Year Treasury',  'asset_type': 'bond',      'description': 'ETF на долгосрочные гособлигации США (20+ лет).'},
    {'ticker': 'IEF',   'name': 'iShares 7-10 Year Treasury', 'asset_type': 'bond',      'description': 'ETF на среднесрочные гособлигации США (7-10 лет).'},
    {'ticker': 'SHY',   'name': 'iShares 1-3 Year Treasury',  'asset_type': 'bond',      'description': 'Краткосрочные гособлигации США. Низкий риск.'},
    {'ticker': 'GLD',   'name': 'SPDR Gold Shares',           'asset_type': 'commodity', 'description': 'ETF на золото. Защитный актив.'},
    {'ticker': 'USO',   'name': 'United States Oil Fund',     'asset_type': 'commodity', 'description': 'ETF на нефть WTI.'},
    {'ticker': 'SLV',   'name': 'iShares Silver Trust',       'asset_type': 'commodity', 'description': 'ETF на серебро.'},
]


class Command(BaseCommand):
    help = 'Заполнить базу стартовыми активами'

    def handle(self, *args, **options):
        created = updated = 0
        for data in ASSETS:
            _, was_created = Asset.objects.update_or_create(
                ticker=data['ticker'],
                defaults={**data, 'current_price': 100, 'previous_close': 100}
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f'Готово! Создано: {created}, обновлено: {updated}. '
            f'Запустите: python manage.py update_prices'
        ))
