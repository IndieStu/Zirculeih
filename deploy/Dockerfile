FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock requirements-dev.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /app/media /app/backend/staticfiles /app/review-mail && chown -R app:app /app && chmod 0700 /app/review-mail
COPY --chown=app:app backend ./backend
ENV PYTHONPATH=/app/backend
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "30", "--access-logfile", "/dev/null"]

FROM base AS test
USER root
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-dev.lock
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app prototypes ./prototypes
COPY --chown=app:app tests ./tests
COPY --chown=app:app docs/branding-artifacts.json ./docs/branding-artifacts.json
COPY --chown=app:app docs/api ./docs/api
USER app
CMD ["python", "-m", "pytest"]
