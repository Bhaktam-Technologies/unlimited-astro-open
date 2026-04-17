#!/bin/sh
exec gunicorn --workers 3 --timeout 12000 -b :5002 -e ENV=$configuration wsgi:app
