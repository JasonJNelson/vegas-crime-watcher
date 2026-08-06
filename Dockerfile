# syntax=docker/dockerfile:1.7
# Vegas Crime Watcher — cache-optimized image for Railway / Docker
# Layer order: base → user → deps (rare) → app code (frequent)

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- Layer 1: OS user (almost never changes) ---
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

# --- Layer 2: dependency metadata (changes only when packages change) ---
COPY --chown=appuser:appuser requirements.txt .

# --- Layer 3: install deps with BuildKit cache mount ---
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ -s requirements.txt ] && grep -vE '^\s*(#|$)' requirements.txt | grep -q .; then \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      echo "stdlib only — skipping pip install"; \
    fi

# --- Layer 4: application code (changes most often → last) ---
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser templates/ templates/

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health', timeout=3)"

CMD ["python", "app.py"]
