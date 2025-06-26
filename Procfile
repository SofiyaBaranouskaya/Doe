web: gunicorn config.wsgi
web: gunicorn config.wsgi --timeout 120
worker: celery -A config worker --loglevel=info
