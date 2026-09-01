FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
        dagster dagster-webserver \
        dlt duckdb \
        dbt-core dbt-duckdb \
        kafka-python

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]
