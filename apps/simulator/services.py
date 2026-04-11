import requests
from datetime import datetime, timedelta, date
from typing import Optional, List
import statistics

YAHOO_BASE   = 'https://query1.finance.yahoo.com/v8/finance/chart/'
YAHOO_SEARCH = 'https://query1.finance.yahoo.com/v1/finance/search'
HEADERS      = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def search_assets(query: str) -> list:
    try:
        resp = requests.get(
            YAHOO_SEARCH,
            params={'q': query, 'quotesCount': 10, 'newsCount': 0},
            headers=HEADERS, timeout=8
        )
        results = []
        for item in resp.json().get('quotes', []):
            q_type = item.get('quoteType', '')
            if q_type not in ('EQUITY', 'ETF', 'MUTUALFUND', 'BOND', 'FUTURE', 'INDEX'):
                continue
            results.append({
                'ticker':   item.get('symbol', ''),
                'name':     item.get('longname') or item.get('shortname', ''),
                'type':     q_type.lower(),
                'exchange': item.get('exchDisp', ''),
            })
        return results[:8]
    except Exception:
        return []


def fetch_current_price(ticker: str) -> Optional[dict]:
    try:
        resp = requests.get(
            f'{YAHOO_BASE}{ticker}',
            params={'interval': '1d', 'range': '5d'},
            headers=HEADERS, timeout=8
        )
        meta  = resp.json()['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice') or meta.get('previousClose')
        if price:
            return {
                'price':    round(float(price), 4),
                'name':     meta.get('longName') or meta.get('shortName', ticker),
                'currency': meta.get('currency', 'USD'),
            }
    except Exception:
        pass
    return None


def fetch_history(ticker: str, period: str = '1y') -> List[dict]:
    """Return list of {'date': 'YYYY-MM-DD', 'close': float} up to today."""
    interval_map = {
        '1mo': ('1d',  '1mo'),
        '3mo': ('1d',  '3mo'),
        '6mo': ('1d',  '6mo'),
        '1y':  ('1wk', '1y'),
        '2y':  ('1wk', '2y'),
        '5y':  ('1mo', '5y'),
    }
    interval, yf_range = interval_map.get(period, ('1wk', '1y'))
    try:
        resp = requests.get(
            f'{YAHOO_BASE}{ticker}',
            params={'interval': interval, 'range': yf_range},
            headers=HEADERS, timeout=10
        )
        result     = resp.json()['chart']['result'][0]
        timestamps = result.get('timestamp', [])
        closes     = result['indicators']['quote'][0].get('close', [])
        today_str  = date.today().isoformat()

        out = []
        for ts, c in zip(timestamps, closes):
            if c is None:
                continue
            d = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
            if d > today_str:          # drop any future-dated points
                continue
            out.append({'date': d, 'close': round(float(c), 4)})

        # Ensure the last point is labelled today if it'js the most recent trading date
        # (Yahoo sometimes returns yesterday). We just relabel, not fabricate a price.
        if out and out[-1]['date'] != today_str:
            out[-1]['date'] = today_str

        return out
    except Exception:
        return []


def _align_series(series_map: dict) -> dict:
    """
    Given {ticker: [{'date', 'close'}]}, find the common date range
    (intersection of dates) so all series start and end at the same points.
    This prevents 'scribble' artefacts when assets have different history lengths.
    """
    if not series_map:
        return {}

    # Build sets of dates per ticker
    date_sets = {tk: set(p['date'] for p in pts) for tk, pts in series_map.items()}
    common    = set.intersection(*date_sets.values()) if date_sets else set()

    if not common:
        return series_map   # fall back to raw if no overlap

    aligned = {}
    for tk, pts in series_map.items():
        aligned[tk] = [p for p in pts if p['date'] in common]
        aligned[tk].sort(key=lambda p: p['date'])
    return aligned


def normalize_series(history: List[dict]) -> List[dict]:
    """Normalise to 100 at the first point so different-priced assets are comparable."""
    if not history:
        return []
    base = history[0]['close']
    if base == 0:
        return [{'date': h['date'], 'value': 100.0} for h in history]
    return [{'date': h['date'], 'value': round(h['close'] / base * 100, 2)} for h in history]


def get_fund_history_normalized(fund_assets_data: List[dict], period: str) -> dict:
    """
    Returns per-asset normalised series, aligned to a common date range.
    fund_assets_data: [{'ticker', 'name', 'color', 'amount'}, ...]
    """
    raw = {}
    for asset in fund_assets_data:
        hist = fetch_history(asset['ticker'], period)
        if hist:
            raw[asset['ticker']] = hist

    aligned = _align_series(raw)

    result = {}
    for asset in fund_assets_data:
        tk   = asset['ticker']
        hist = aligned.get(tk)
        if hist:
            result[tk] = {
                'label': asset['name'] or tk,
                'color': asset['color'],
                'data':  normalize_series(hist),
            }
    return result


def get_weighted_fund_series(fund_assets_data: List[dict], period: str) -> List[dict]:
    """Weighted average normalised performance of the whole fund."""
    total_amount = sum(a['amount'] for a in fund_assets_data)
    if total_amount == 0:
        return []

    raw = {}
    for asset in fund_assets_data:
        hist = fetch_history(asset['ticker'], period)
        if hist:
            raw[asset['ticker']] = hist

    aligned = _align_series(raw)

    all_series: dict = {}
    for asset in fund_assets_data:
        tk     = asset['ticker']
        hist   = aligned.get(tk)
        if not hist:
            continue
        weight = asset['amount'] / total_amount
        norm   = normalize_series(hist)
        for point in norm:
            d = point['date']
            all_series.setdefault(d, 0.0)
            all_series[d] += point['value'] * weight

    return [{'date': d, 'value': round(v, 2)} for d, v in sorted(all_series.items())]


def forecast(history: List[dict], months: int) -> Optional[dict]:
    """
    Three-scenario forecast based on mean daily return and historical volatility.
    Scenarios:  base = mean, optimistic = mean + 1σ, pessimistic = mean − 1σ
    Returns normalised series (base=100 at last historical point).
    """
    if len(history) < 15:
        return None

    closes  = [h['close'] for h in history]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

    mean_r = statistics.mean(returns)
    std_r  = statistics.stdev(returns) if len(returns) > 1 else 0.0

    steps     = months * 22          # approx trading days per month
    last_date = datetime.strptime(history[-1]['date'], '%Y-%m-%d')

    def build_scenario(daily_r: float) -> List[dict]:
        pts   = []
        price = 1.0   # normalised base = 1
        for i in range(1, steps + 1):
            price *= (1 + daily_r)
            d      = last_date + timedelta(days=int(i * 365 / 252))
            pts.append({'date': d.strftime('%Y-%m-%d'), 'value': round(price * 100, 2)})
        # Thin to ~24 points for clean chart lines
        step = max(1, len(pts) // 24)
        return pts[::step]

    return {
        'optimistic':  build_scenario(mean_r + std_r),
        'base':        build_scenario(mean_r),
        'pessimistic': build_scenario(mean_r - std_r),
    }
