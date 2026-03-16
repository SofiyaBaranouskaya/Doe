from django.db import models
from django.conf import settings
import decimal


ASSET_COLORS = [
    '#6EE7B7', '#60A5FA', '#F9A8D4', '#FCD34D', '#A78BFA',
    '#34D399', '#F87171', '#FBBF24', '#818CF8', '#2DD4BF',
    '#FB923C', '#E879F9', '#4ADE80', '#38BDF8', '#FB7185',
]


class Fund(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='funds')
    name = models.CharField(max_length=100, verbose_name='Название фонда')
    description = models.TextField(blank=True, verbose_name='Описание')
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Общая сумма')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Фонд'
        verbose_name_plural = 'Фонды'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.user.email})'

    @property
    def total_invested(self):
        return sum(a.amount for a in self.assets.all())

    @property
    def unallocated(self):
        return self.total_amount - self.total_invested


class FundAsset(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='assets')
    ticker = models.CharField(max_length=20, verbose_name='Тикер')
    name = models.CharField(max_length=200, verbose_name='Название')
    asset_type = models.CharField(max_length=20, default='stock', verbose_name='Тип')
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Сумма вложения')
    color = models.CharField(max_length=10, default='#6EE7B7')
    added_at = models.DateTimeField(auto_now_add=True)

    # Кэшированные данные цен
    price_at_add = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    current_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    last_price_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Актив фонда'
        verbose_name_plural = 'Активы фонда'
        ordering = ['added_at']

    def __str__(self):
        return f'{self.ticker} в {self.fund.name}'

    @property
    def allocation_percent(self):
        if self.fund.total_amount > 0:
            return float(self.amount) / float(self.fund.total_amount) * 100
        return 0

    @property
    def pnl_percent(self):
        if self.price_at_add and self.current_price and self.price_at_add > 0:
            return (float(self.current_price) - float(self.price_at_add)) / float(self.price_at_add) * 100
        return 0

    @property
    def pnl_amount(self):
        return float(self.amount) * self.pnl_percent / 100