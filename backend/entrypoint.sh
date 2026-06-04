#!/bin/sh
set -e

echo "Running checks"
python manage.py check

echo "Running Django migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Always run ASGI server so WebSocket routes are available in all environments.
if [ "$DJANGO_ENV" = "development" ]; then
    echo "Starting Daphne ASGI server (development mode)..."
else
    echo "Starting Daphne ASGI server..."
fi

exec daphne -b 0.0.0.0 -p 8000 main.asgi:application