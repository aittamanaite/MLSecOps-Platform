# Cybersecurity Threat Detection MLOps Platform

## 1. Overview
An end-to-end MLOps platform for real-time cybersecurity log processing, ML-based anomaly detection, and alerting. The system leverages Dagster for orchestration, Redpanda (Kafka) for streaming, dbt with DuckDB for transformations, and MLflow for model tracking.

## 2. What the pipeline does
1. **Producer**: Ingests raw network traffic logs (CSV) and streams them to Redpanda.
2. **Cleaner**: Consumes raw logs, standardizes and cleans the data, then streams it to a cleaned logs topic.
3. **Training**: Trains an Isolation Forest anomaly detection model on cleaned data and logs metrics/models to MLflow.
4. **Inference**: Applies the trained ML model in real-time on the cleaned stream to detect cyber-attacks.
5. **Alerting**: Streams detected anomalies to an application errors topic.
6. **Analytics (dbt)**: Transforms and models the processed data for dashboards and reporting.
7. **Quality Gates**: Ensures data integrity at every step (raw, cleaned, inference).

## 3. Architecture diagram
```text
[Raw CSVs] 
    |
(Quality Gate 1: Raw Data)
    v
[Producer] -> [Kafka: raw-logs] 
    |
    v
[Cleaner] -> [Kafka: cleaned-logs]
    |
(Quality Gate 2: Cleaned Data)
    |
    +-----> [Model Training (MLflow)]
    |
    v
[Inference] -> [Kafka: app-errors]
    |
(Quality Gate 3: Inference Output)
```

## 4. Quick Start
1. Run `docker compose up --build`
2. Access Dagster UI at `http://localhost:3000`
3. Access MLflow UI at `http://localhost:5000`

## 5. Services
To start services individually:
- **Redpanda**: `docker compose up redpanda`
- **Dagster**: `dagster dev` (starts both webserver and daemon)
- **MLflow**: `mlflow ui`
- **dbt**: Run transformations via `dbt run`

## 6. ML Pipeline
The platform uses an Isolation Forest model for unsupervised anomaly detection. 
- **Training**: The model is trained on cleaned network logs.
- **Tracking**: MLflow is used to track model parameters, metrics (precision, recall, F1), and artifacts.
- **Registry**: Trained models are registered and versioned in the MLflow Model Registry.

## 7. Data Quality Gates
- **Raw CSV Gate**: Validates the schema and completeness of raw CSV files before ingestion.
- **Cleaned Data Gate**: Ensures standard formatting, valid IPs, and complete records after the cleaning phase.
- **Inference Output Gate**: Checks the structure of anomaly alerts and prediction confidence scores.

## 8. Data locations
- Raw Data: `data/raw/`
- Cleaned Exports: `data/exports/cleaned_logs.jsonl`
- Inference Alerts: `data/exports/app_errors.jsonl`
- DuckDB Database: `data/warehouse/`

## 9. Manual commands
- **Producer**: `python -m src.streaming.producer`
- **Cleaner**: `python -m src.streaming.cleaner`
- **Inference**: `python -m src.streaming.inference`
- **Training**: `python -m src.ml.train`
- **dbt**: `dbt run` / `dbt test`

## 10. Project structure
```text
MLSecOps-Platform/
├── data/
│   ├── raw/
│   ├── exports/
│   └── warehouse/
├── src/
│   ├── streaming/
│   │   ├── producer.py
│   │   ├── cleaner.py
│   │   └── inference.py
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── assets.py
│   │   └── definitions.py
│   ├── quality/
│   │   └── data_quality.py
│   └── ml/
│       └── train.py
├── dbt/
├── tests/
├── docker-compose.yml
└── README.md
```

## 11. Testing
Run tests using pytest:
```bash
pytest tests/
```

## 12. Notes
- For production deployment, ensure Redpanda is properly clustered and MLflow is backed by a persistent database (e.g., PostgreSQL).
- Environment variables can be adjusted for batch sizing and throughput control.
