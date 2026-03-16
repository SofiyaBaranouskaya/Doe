from django.urls import path
from . import views

app_name = 'simulator'

urlpatterns = [
    # Страницы
    path('', views.fund_list, name='fund_list'),
    path('create/', views.fund_create, name='fund_create'),
    path('<int:pk>/', views.fund_detail, name='fund_detail'),

    # Действия с активами
    path('<int:pk>/add-asset/', views.add_asset, name='add_asset'),
    path('<int:pk>/remove-asset/<int:asset_id>/', views.remove_asset, name='remove_asset'),
    path('<int:pk>/refresh-prices/', views.refresh_prices_api, name='refresh_prices'),
    path('<int:pk>/delete/', views.fund_delete, name='fund_delete'),

    # API данных
    path('api/search/', views.search_assets_api, name='search_assets'),
    path('api/chart/<int:pk>/', views.chart_data_api, name='chart_data'),
    path('api/all-funds-chart/', views.all_funds_chart_api, name='all_funds_chart'),
]