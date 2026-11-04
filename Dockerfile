# Production-style single-origin image: one web process for Vite React and FastAPI.
# No API credentials are baked into the image; configure them in the host environment.
FROM node:22-alpine AS frontend-build
WORKDIR /site
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MASR_USER_DB=/app/data/traveler.sqlite3 \
    DATABASE_PATH=/app/data/tourism.db \
    PORT=10000
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/quick_demo ./quick_demo
COPY scripts/storage_backup.py /app/scripts/storage_backup.py
COPY --from=frontend-build /site/dist /app/frontend/dist
RUN groupadd -g 10001 masr && useradd -u 10001 -g masr -m masr \
    && mkdir -p /app/data && chown -R masr:masr /app/data
USER masr
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=6s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('PORT','10000') + '/api/ready', timeout=5)" || exit 1
CMD ["sh", "-c", "exec uvicorn app.main:app --no-proxy-headers --host 0.0.0.0 --port ${PORT:-10000}"]
