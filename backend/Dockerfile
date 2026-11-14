# syntax=docker/dockerfile:1
FROM python:3.14.9-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY requirements/ requirements/

# --- Development image: dev tools, source bind-mounted by docker-compose.yml ---
FROM base AS development
RUN pip install -r requirements/dev.txt
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- Production image: Gunicorn, no dev dependencies ---
FROM base AS production
ENV DJANGO_SETTINGS_MODULE=config.settings.production
RUN pip install -r requirements/prod.txt
COPY --chown=app:app . .
RUN mkdir -p staticfiles media && chown app:app staticfiles media
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
