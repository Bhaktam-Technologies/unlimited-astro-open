#!/bin/sh
export GOOGLE_APPLICATION_CREDENTIALS="unlimitedastro-"$configuration".json"

# Start Celery worker in background — handles NOW + LATER scheduled notifications
celery -A celery_app.celery worker --loglevel=info --concurrency=2 -n notification_worker@%h &

##exec gunicorn --chdir /unlimitedastro_processor --workers 3 --timeout 120 --log-level=debug --bind 0.0.0.0:80 wsgi:app
#exec gunicorn -b :5002 - unlimitedastro_processor:app
#-e env=dev
#exec gunicorn --reload --workers 3 --timeout 12000 -b :5002 -e ENV=prod wsgi:app
exec gunicorn --workers 3 --timeout 12000 -b :5002 -e ENV=$configuration wsgi:app
# ALLOW_PUBLIC_ACCESS=1 gunicorn --workers 3 --timeout 12000 -b :5002 wsgi:app --reload
#  lsof -t -i :5002 | xargs kill -9