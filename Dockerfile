FROM python:3.11-slim

# Environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements.txt

# Copy project files
COPY . /app

# Create non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Railway provides PORT automatically
EXPOSE 8000

# Start Django in production
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn cosmic_watch.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 4 \
    --timeout 120
