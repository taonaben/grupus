#!/bin/sh
set -e

echo "Running checks"
python manage.py check

echo "Running Django migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Check if we're in development mode (default to production)
if [ "$DJANGO_ENV" = "development" ]; then
    echo "Starting Django development server with auto-reload..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting Daphne ASGI server..."
    exec daphne -b 0.0.0.0 -p 8000 main.asgi:application
fi