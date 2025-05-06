# app_service/Dockerfile

# ── Stage 1: build runtime environment ──────────────────────────────────────────
FROM python:3.12-slim AS python-base

# System deps
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install Pipenv (locked install → system site‑packages)
RUN pip install --no-cache-dir pipenv==2023.12.1

# ── Stage 2: copy source, install deps ─────────────────────────────────────────
WORKDIR /code
# Pipenv files first
COPY Pipfile Pipfile.lock* ./
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --system

# 👇  install Gunicorn outside Pipenv (quick fix)
RUN pip install --no-cache-dir gunicorn==21.2.0 whitenoise==6.6.0

# Copy the rest of the Django project
COPY . .

# create static & collectstatic target
RUN mkdir -p /code/static /code/staticfiles

# ── Runtime configuration ──────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=app_service.settings

# Expose Django dev port
EXPOSE 8000

# Entrypoint runs DB migrations then launches gunicorn
CMD ["bash", "-c", \
"python manage.py migrate --noinput && \
python manage.py collectstatic --noinput && \
gunicorn app_service.wsgi:application \
        --bind 0.0.0.0:8000 --workers 3 --timeout 180"]