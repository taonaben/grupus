#!/bin/bash
set -e

echo "Running checks"
python manage.py check

echo "Running Django migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Daphne ASGI server..."
# Use Daphne for WebSocket support (required for Django Channels)
exec daphne -b 0.0.0.0 -p 8000 main.asgi:application