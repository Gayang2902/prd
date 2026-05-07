FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY packages/shared-schemas /tmp/shared-schemas
RUN pip install --no-cache-dir /tmp/shared-schemas && rm -rf /tmp/shared-schemas

COPY apps/backend/ .
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
