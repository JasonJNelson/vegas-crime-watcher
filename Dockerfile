# Vegas Crime Watcher — production image for Railway / any container host
# Pure Python (stdlib only) → small image, no pip packages required.

FROM python:3.12-slim-bookworm

# Avoid .pyc files and force unbuffered logs (better for Railway log stream)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app

# Create non-root user (Railway runs as root by default, but this is safer elsewhere)
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

# Copy only what we need (layer-friendly; no pip install for this app)
COPY --chown=appuser:appuser app.py requirements.txt ./
COPY --chown=appuser:appuser templates/ templates/

USER appuser

# Document the port (Railway injects $PORT at runtime)
EXPOSE 8080

# Healthcheck for local docker / orchestrators that honor HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/api/health', timeout=3)"

CMD ["python", "app.py"]
