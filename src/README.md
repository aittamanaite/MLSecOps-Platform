# 📂 Source Code (`src/`)

This directory contains the core logic for the MLSecOps streaming pipeline, orchestration, and machine learning components.

## 📁 Directory Structure

### `src/ingestion/`
- Contains scripts for initial data setup.
- `ingest.py`: Entry point to prepare the `data/raw/` folder and receive data.

### `src/streaming/`
Real-time processing logic using Kafka (Redpanda):
- `producer.py`: Simulates real-time traffic by chunking CSVs and sending them to Kafka topic `raw-logs`.
- `cleaner.py`: Consumes raw messages, enforces strict data formats, handles unicode encoding anomalies (cp1252 artifacts), and publishes to `cleaned-logs`.
- `inference.py`: Evaluates incoming clean records against the trained ML model and generates confidence scores. Detected anomalies are routed to the `alerts` topic.

### `src/orchestration/`
Dagster orchestrator definitions:
- `assets.py`: Defines the core data assets representing the pipeline steps:
  - `streaming_ingestion_asset`: Reads local CSV data and publishes to `raw-logs` with raw data quality validation.
  - `streaming_cleaning_asset`: Consumes from `raw-logs`, cleans records, and outputs to `cleaned-logs` with cleaned data quality validation.
  - `model_training_asset`: Trains the Random Forest model on cleaned data and tracks metrics in MLflow.
  - `model_inference_asset`: Consumes cleaned data, applies ML inference, and routes anomalies to `alerts`.
- `definitions.py`: Combines assets into a complete Dagster definition with the main `realtime_mlsecops_job`, sensors, and schedules.

### `src/quality/`
Strict Data Quality gates:
- `data_quality.py`: Defines validation rules for raw schemas, post-cleaning formats, and inference outputs. Ensures end-to-end data integrity with three validation stages (Raw, Cleaned, Inference).

### `src/ml/`
Machine Learning logic:
- `features.py`: Feature extraction from CICIDS2017 network flow records and StandardScaler normalization.
- `train.py`: Supervised learning (RandomForestClassifier) with strict 80/20 stratified train/test split. Logs parameters, metrics, tags, descriptions, and model artifacts to MLflow.
- `predict.py`: Loads the registered model and scaler to perform real-time predictions with confidence scoring.

## 🚀 Execution

All components are orchestrated via **Dagster**. When you click *Materialize All* in the Dagster UI (`http://localhost:3000`), it executes these modules in the correct dependency order.
