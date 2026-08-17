FROM python:3.12-slim

WORKDIR /app

# Ensure Python can find the app package (needed by Alembic migrations)
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create storage directory
RUN mkdir -p /app/storage_data

EXPOSE 8000

# Entrypoint script handles migrations + startup
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
