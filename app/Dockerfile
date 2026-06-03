# =====================================================================
# COMPASS — Databricks App image
#   Multi-stage: builds the React frontend, then a slim FastAPI runtime
#   that serves both the API and the static frontend bundle.
# =====================================================================

# ---------- Stage 1: build the React frontend ----------
FROM node:20-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./frontend/
RUN cd frontend && npm install --no-audit --no-fund
COPY frontend ./frontend
RUN cd frontend && npm run build

# ---------- Stage 2: Python runtime ----------
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=frontend /build/frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    COMPASS_AGENT_MODE=lite

EXPOSE 8080
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
