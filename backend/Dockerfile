# backend/Dockerfile
# Multi-stage build for the REVVY FastAPI backend.
#
# ASSUMPTIONS (verify once BACKEND-AGENT / DATABASE-AGENT finish scaffolding):
#   - App entrypoint lives at backend/app/main.py and exposes `app = FastAPI()`
#     -> CMD below runs `uvicorn app.main:app`. Update if the module/attr differs.
#   - Alembic config lives at backend/alembic.ini with migrations in backend/alembic/
#   - backend/requirements.txt is the single source of Python deps (shared file,
#     see header comment in that file).

# ---- Stage 1: builder ---------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Build-time system deps needed to compile any C-extension wheels
# (psycopg2-binary ships prebuilt wheels, but gcc/libpq-dev keeps this
# resilient if a transitive dependency needs to compile).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install into the user site-packages dir so it can be copied wholesale
# into the slim runtime image below (keeps final image free of gcc/apt state).
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: runtime ----------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime needs the Postgres client library for psycopg2 at import time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Bring over installed Python packages from the builder stage.
COPY --from=builder /root/.local /home/appuser/.local

# Application code.
COPY ./app ./app
COPY alembic.ini .
COPY ./alembic ./alembic

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN chown -R appuser:appuser /app /home/appuser/.local

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
