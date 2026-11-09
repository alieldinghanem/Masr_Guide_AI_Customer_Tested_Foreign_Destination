FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Run as an unprivileged user; /app/data is the only writable location (SQLite cache).
RUN useradd --create-home --uid 10001 app && mkdir -p /app/data && chown -R app:app /app
COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/quick_demo ./quick_demo
COPY --chown=app:app frontend/src/coastalDestinations.json /app/frontend/src/coastalDestinations.json
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1
CMD ["uvicorn", "app.main:app", "--no-proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
