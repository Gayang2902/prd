FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY packages/shared-schemas /tmp/shared-schemas
RUN pip install --no-cache-dir /tmp/shared-schemas && rm -rf /tmp/shared-schemas

COPY apps/backend/ .
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["sh", "entrypoint.sh"]
