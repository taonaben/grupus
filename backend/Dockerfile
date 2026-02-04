FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && apt-get clean

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN sed -i 's/\r$//' entrypoint.sh

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

# Add this to see import errors:
RUN python -c "import django; django.setup()" || echo "Django setup failed - check imports"

# Use Daphne ASGI server for WebSocket support
# Can be overridden by entrypoint.sh or environment
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "main.asgi:application"]