# apps/users/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# Метрики для контента
content_started = Counter(
    'content_started_total',
    'Total number of content started',
    ['content_type', 'content_id', 'page']
)

content_completed = Counter(
    'content_completed_total',
    'Total number of content completed',
    ['content_type', 'content_id', 'page']
)

user_actions = Counter(
    'user_actions_total',
    'User actions counter',
    ['user_id', 'action_type', 'content_type']
)

content_time_spent = Histogram(
    'content_time_spent_seconds',
    'Time spent on content',
    ['content_type', 'content_id', 'page'],
    buckets=(30, 60, 120, 300, 600, 900, 1800, 3600)
)

# Метрики для пользователей
active_users = Gauge(
    'active_users',
    'Number of active users',
    ['period']
)

user_logins = Counter(
    'user_logins_total',
    'Total number of user logins',
    ['user_id']
)

# ДОБАВЬТЕ ЭТИ МЕТРИКИ (для middleware и других файлов)
user_sessions = Counter(
    'user_sessions_total',
    'Total number of user sessions',
    ['user_id', 'is_authenticated']
)

page_views = Counter(
    'page_views_total',
    'Total page views',
    ['page_name', 'user_authenticated']
)

page_load_time = Histogram(
    'page_load_time_seconds',
    'Page load time',
    ['page_name'],
    buckets=(0.1, 0.5, 1, 2, 5, 10)
)

api_requests = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method'],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5)
)

total_users = Gauge(
    'total_users',
    'Total number of registered users'
)

completed_content_per_user = Gauge(
    'completed_content_per_user',
    'Average completed content per user'
)

daily_active_users = Gauge(
    'daily_active_users',
    'Daily active users'
)

weekly_active_users = Gauge(
    'weekly_active_users',
    'Weekly active users'
)

monthly_active_users = Gauge(
    'monthly_active_users',
    'Monthly active users'
)

# Декоратор для измерения времени
def measure_time(metric_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            print(f"{metric_name} took {duration} seconds")
            return result
        return wrapper
    return decorator