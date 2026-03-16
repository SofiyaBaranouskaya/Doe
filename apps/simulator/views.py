from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
import json

from .models import Fund, FundAsset, ASSET_COLORS
from . import services


# ───────────────────────────────────────────
# Список фондов пользователя
# ───────────────────────────────────────────
@login_required
def fund_list(request):
    funds = Fund.objects.filter(user=request.user).prefetch_related('assets')

    funds_data = []
    for fund in funds:
        assets = list(fund.assets.all())
        total_pnl = sum(a.pnl_amount for a in assets)
        total_pnl_pct = (total_pnl / float(fund.total_amount) * 100) if fund.total_amount else 0
        funds_data.append({
            'obj': fund,
            'assets_count': len(assets),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'colors': [a.color for a in assets[:5]],
        })

    return render(request, 'simulator/fund_list.html', {'funds': funds_data})


# ───────────────────────────────────────────
# Создание фонда
# ───────────────────────────────────────────
@login_required
def fund_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        total_amount = request.POST.get('total_amount', '0').strip()
        description = request.POST.get('description', '').strip()

        if not name or not total_amount:
            return render(request, 'simulator/fund_create.html', {'error': 'Заполните все поля'})

        try:
            amount = float(total_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return render(request, 'simulator/fund_create.html', {'error': 'Некорректная сумма'})

        fund = Fund.objects.create(
            user=request.user,
            name=name,
            description=description,
            total_amount=amount,
        )
        return redirect('simulator:fund_detail', pk=fund.pk)

    return render(request, 'simulator/fund_create.html')


# ───────────────────────────────────────────
# Страница фонда — главная
# ───────────────────────────────────────────
@login_required
def fund_detail(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    assets = list(fund.assets.all())

    assets_data = []
    for a in assets:
        assets_data.append({
            'id': a.id,
            'ticker': a.ticker,
            'name': a.name,
            'asset_type': a.asset_type,
            'amount': float(a.amount),
            'allocation_pct': round(a.allocation_percent, 1),
            'color': a.color,
            'price_at_add': float(a.price_at_add) if a.price_at_add else None,
            'current_price': float(a.current_price) if a.current_price else None,
            'pnl_pct': round(a.pnl_percent, 2),
            'pnl_amount': round(a.pnl_amount, 2),
        })

    total_pnl = sum(a['pnl_amount'] for a in assets_data)
    total_pnl_pct = (total_pnl / float(fund.total_amount) * 100) if fund.total_amount else 0

    used_colors = [a.color for a in assets]
    next_color = next((c for c in ASSET_COLORS if c not in used_colors), ASSET_COLORS[0])

    context = {
        'fund': fund,
        'assets': assets_data,
        'assets_json': json.dumps(assets_data),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl_pct, 2),
        'unallocated': float(fund.unallocated),
        'next_color': next_color,
        'available_colors': ASSET_COLORS,
        'periods': [('1mo','1 мес'),('3mo','3 мес'),('6mo','6 мес'),('1y','1 год'),('2y','2 года'),('5y','5 лет')],
    }
    return render(request, 'simulator/fund_detail.html', context)


# ───────────────────────────────────────────
# Добавить актив в фонд
# ───────────────────────────────────────────
@login_required
@require_POST
def add_asset(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    try:
        data = json.loads(request.body)
        ticker = data.get('ticker', '').upper().strip()
        amount = float(data.get('amount', 0))
        color = data.get('color', ASSET_COLORS[0])

        if not ticker or amount <= 0:
            return JsonResponse({'success': False, 'error': 'Некорректные данные'})

        if amount > float(fund.unallocated):
            return JsonResponse({'success': False, 'error': f'Превышен нераспределённый остаток: {float(fund.unallocated):.2f}'})

        # Получаем текущую цену
        price_data = services.fetch_current_price(ticker)
        if not price_data:
            return JsonResponse({'success': False, 'error': f'Не удалось найти тикер {ticker}'})

        asset = FundAsset.objects.create(
            fund=fund,
            ticker=ticker,
            name=price_data['name'],
            asset_type=data.get('asset_type', 'stock'),
            amount=amount,
            color=color,
            price_at_add=price_data['price'],
            current_price=price_data['price'],
            last_price_update=timezone.now(),
        )

        return JsonResponse({
            'success': True,
            'asset': {
                'id': asset.id,
                'ticker': asset.ticker,
                'name': asset.name,
                'amount': float(asset.amount),
                'allocation_pct': round(asset.allocation_percent, 1),
                'color': asset.color,
                'price_at_add': float(asset.price_at_add),
                'current_price': float(asset.current_price),
                'pnl_pct': 0,
                'pnl_amount': 0,
            },
            'unallocated': float(fund.unallocated),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ───────────────────────────────────────────
# Удалить актив
# ───────────────────────────────────────────
@login_required
@require_POST
def remove_asset(request, pk, asset_id):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    asset = get_object_or_404(FundAsset, pk=asset_id, fund=fund)
    asset.delete()
    return JsonResponse({'success': True, 'unallocated': float(fund.unallocated)})


# ───────────────────────────────────────────
# API: Поиск активов
# ───────────────────────────────────────────
@login_required
@require_GET
def search_assets_api(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 1:
        return JsonResponse({'results': []})
    results = services.search_assets(query)
    return JsonResponse({'results': results})


# ───────────────────────────────────────────
# API: Исторические данные для графика
# ───────────────────────────────────────────
@login_required
@require_GET
def chart_data_api(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    period = request.GET.get('period', '1y')
    mode = request.GET.get('mode', 'history')   # history | forecast
    forecast_months = int(request.GET.get('months', 12))

    assets = list(fund.assets.all())
    if not assets:
        return JsonResponse({'series': [], 'fund_series': []})

    assets_data = [{'ticker': a.ticker, 'name': a.name, 'color': a.color, 'amount': float(a.amount)} for a in assets]

    if mode == 'forecast':
        # Возвращаем прогноз для каждого актива
        forecast_result = {}
        for asset in assets_data:
            hist = services.fetch_history(asset['ticker'], '2y')
            if hist:
                fc = services.forecast(hist, forecast_months)
                if fc:
                    forecast_result[asset['ticker']] = {
                        'label': asset['name'] or asset['ticker'],
                        'color': asset['color'],
                        'scenarios': fc,
                    }
        return JsonResponse({'forecast': forecast_result, 'mode': 'forecast'})
    else:
        series = services.get_fund_history_normalized(assets_data, period)
        fund_series = services.get_weighted_fund_series(assets_data, period)
        return JsonResponse({'series': series, 'fund_series': fund_series, 'mode': 'history'})


# ───────────────────────────────────────────
# API: Обновить текущие цены активов фонда
# ───────────────────────────────────────────
@login_required
@require_POST
def refresh_prices_api(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    updated = []
    for asset in fund.assets.all():
        price_data = services.fetch_current_price(asset.ticker)
        if price_data:
            asset.current_price = price_data['price']
            asset.last_price_update = timezone.now()
            asset.save(update_fields=['current_price', 'last_price_update'])
            updated.append({
                'id': asset.id,
                'ticker': asset.ticker,
                'current_price': float(asset.current_price),
                'pnl_pct': round(asset.pnl_percent, 2),
                'pnl_amount': round(asset.pnl_amount, 2),
            })
    return JsonResponse({'updated': updated})


# ───────────────────────────────────────────
# API: Общий график всех фондов пользователя
# ───────────────────────────────────────────
@login_required
@require_GET
def all_funds_chart_api(request):
    period = request.GET.get('period', '1y')
    funds = Fund.objects.filter(user=request.user).prefetch_related('assets')

    palette = ['#6EE7B7', '#60A5FA', '#F9A8D4', '#FCD34D', '#A78BFA', '#FB923C']
    result = []
    for i, fund in enumerate(funds):
        assets_data = [{'ticker': a.ticker, 'name': a.name, 'color': a.color, 'amount': float(a.amount)}
                       for a in fund.assets.all()]
        if not assets_data:
            continue
        series = services.get_weighted_fund_series(assets_data, period)
        result.append({
            'fund_id': fund.id,
            'fund_name': fund.name,
            'color': palette[i % len(palette)],
            'data': series,
        })
    return JsonResponse({'funds': result})


# ───────────────────────────────────────────
# Удалить фонд
# ───────────────────────────────────────────
@login_required
@require_POST
def fund_delete(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    fund.delete()
    return JsonResponse({'success': True})