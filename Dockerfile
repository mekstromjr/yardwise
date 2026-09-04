FROM python:3.12.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.7.17 /uv /uvx /bin/

WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Dependency layer first so it caches across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY manage.py ./
COPY config/ config/
COPY garden/ garden/
COPY templates/ templates/
COPY static/ static/

# collectstatic at build time; whitenoise serves from the baked-in manifest.
RUN DJANGO_STATIC_ROOT=/app/staticfiles /app/.venv/bin/python manage.py collectstatic --noinput

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/media && chown -R app:app /data/media
USER app

EXPOSE 8000
# Migrations run on start: single-replica app, so this is safe and means a new
# image version needs no manual migration step - important for the handover.
CMD ["/bin/sh", "-c", "/app/.venv/bin/python manage.py migrate --noinput && exec /app/.venv/bin/gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3 --timeout 90"]
