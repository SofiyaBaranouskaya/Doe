# from django.contrib import admin
# from .models import Fund, FundAsset
#
#
# class FundAssetInline(admin.TabularInline):
#     model = FundAsset
#     extra = 0
#     readonly_fields = ('added_at', 'price_at_add', 'current_price', 'last_price_update')
#     fields = ('ticker', 'name', 'asset_type', 'amount', 'color', 'price_at_add', 'current_price', 'last_price_update')
#
#
# @admin.register(Fund)
# class FundAdmin(admin.ModelAdmin):
#     list_display = ('name', 'user', 'total_amount', 'total_invested_display', 'assets_count', 'created_at')
#     list_filter = ('created_at',)
#     search_fields = ('name', 'user__email')
#     readonly_fields = ('created_at', 'updated_at')
#     inlines = [FundAssetInline]
#
#     def total_invested_display(self, obj):
#         return f'{float(obj.total_invested):.2f}'
#     total_invested_display.short_description = 'Invested'
#
#     def assets_count(self, obj):
#         return obj.assets.count()
#     assets_count.short_description = 'Assets'
#
#
# @admin.register(FundAsset)
# class FundAssetAdmin(admin.ModelAdmin):
#     list_display = ('ticker', 'name', 'fund', 'amount', 'price_at_add', 'current_price', 'pnl_display', 'added_at')
#     list_filter = ('asset_type',)
#     search_fields = ('ticker', 'name', 'fund__name')
#     readonly_fields = ('added_at', 'last_price_update')
#
#     def pnl_display(self, obj):
#         pct = obj.pnl_percent
#         sign = '+' if pct >= 0 else ''
#         return f'{sign}{pct:.2f}%'
#     pnl_display.short_description = 'P/E'