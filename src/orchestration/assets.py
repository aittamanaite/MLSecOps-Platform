"""Dagster assets for the MLSecOps streaming and ML pipeline."""

import os
import glob
import json

import numpy as np
import pandas as pd
from dagster import asset, AssetExecutionContext, MetadataValue

from src.streaming.producer import run_producer, get_project_root
from src.streaming.cleaner import run_cleaner
from src.streaming.inference import run_inference
from src.quality.data_quality import (
    validate_raw_csv,
    validate_cleaned_records,
    validate_inference_output,
    DataQualityError,
)


def _target_records() -> int:
    """Target volume per micro-batch (overridable via STREAM_MAX_RECORDS)."""
    return int(os.getenv("STREAM_MAX_RECORDS", "120000"))


def _read_batch_size() -> int:
    return int(os.getenv("PRODUCER_BATCH_SIZE", "5000"))


def _chunk_stride() -> int:
    """1 = sequential; >1 = spread sample across the full day (more attacks)."""
    return max(1, int(os.getenv("PRODUCER_CHUNK_STRIDE", "1")))


@asset(
    group_name="streaming_pipeline",
    compute_kind="python",
    description="Simulates real-time network traffic by publishing local CSVs to Redpanda (raw-logs).",
)
def streaming_ingestion_asset(context: AssetExecutionContext):
    """Ingest raw CSV files into Kafka/Redpanda with data quality validation."""
    target = _target_records()
    context.log.info(f"Starting real-time ingestion to Kafka/Redpanda (target {target} events)...")

    # ── DATA QUALITY GATE: Validate raw CSV files before ingestion ──
    project_root = get_project_root()
    data_dir = os.path.join(project_root, "data", "raw")
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))

    for filepath in csv_files:
        context.log.info(f"Quality check on: {os.path.basename(filepath)}")
        df = pd.read_csv(filepath, keep_default_na=False, nrows=10000)
        # Replace infinite values with NaN, mirroring the sanitization the
        # producer applies (_sanitize_chunk) before publishing to Kafka.
        # CICIDS2017 flow-rate columns (e.g. Flow Bytes/s) naturally produce
        # +/-inf when Flow Duration is 0, so this reflects real pipeline data.
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
        try:
            report = validate_raw_csv(df)
            context.log.info(
                f"✅ Raw data quality PASSED for {os.path.basename(filepath)} "
                f"({report.passed_rules}/{report.total_rules} rules passed)"
            )
        except DataQualityError as e:
            context.log.error(f"❌ Raw data quality FAILED for {os.path.basename(filepath)}")
            context.log.error(e.report.summary())
            raise

    events_published = run_producer(
        batch_size=_read_batch_size(),
        max_records=target,
        chunk_stride=_chunk_stride(),
    )
    context.log.info(f"{events_published} events published to raw stream.")
    context.add_output_metadata(
        {
            "events_published": MetadataValue.int(events_published),
            "target_records": MetadataValue.int(target),
        }
    )
    return events_published


@asset(
    deps=[streaming_ingestion_asset],
    group_name="streaming_pipeline",
    compute_kind="python",
    description="Consumes raw stream, cleans records, and publishes to cleaned-logs.",
)
def streaming_cleaning_asset(context: AssetExecutionContext):
    """Clean streaming data with post-cleaning quality validation."""
    target = _target_records()
    context.log.info(f"Starting stream cleaning (target {target} events)...")
    cleaned = run_cleaner(max_messages=target)
    context.log.info(f"{cleaned} events cleaned and published.")

    # ── DATA QUALITY GATE: Validate cleaned export ──
    project_root = get_project_root()
    export_path = os.path.join(project_root, "data", "exports", "cleaned_logs.jsonl")
    if os.path.exists(export_path):
        records = []
        with open(export_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        if records:
            try:
                report = validate_cleaned_records(records)
                context.log.info(
                    f"✅ Cleaned data quality PASSED "
                    f"({report.passed_rules}/{report.total_rules} rules passed)"
                )
            except DataQualityError as e:
                context.log.error("❌ Cleaned data quality FAILED")
                context.log.error(e.report.summary())
                raise

    context.add_output_metadata(
        {
            "events_cleaned": MetadataValue.int(cleaned),
            "export_path": MetadataValue.path("data/exports/cleaned_logs.jsonl"),
        }
    )
    return cleaned


@asset(
    deps=[streaming_cleaning_asset],
    group_name="ml_pipeline",
    compute_kind="machine_learning",
    description="Trains an Isolation Forest anomaly detection model and logs to MLflow.",
)
def model_training_asset(context: AssetExecutionContext):
    """Train the ML model on cleaned data and register with MLflow."""
    context.log.info("Starting ML model training...")

    try:
        from src.ml.train import run_training

        project_root = get_project_root()
        data_path = os.path.join(project_root, "data", "exports", "cleaned_logs.jsonl")

        if not os.path.exists(data_path):
            context.log.warning(f"Training data not found at {data_path}. Skipping training.")
            return {"status": "skipped", "reason": "no_training_data"}

        result = run_training(data_path=data_path)
        context.log.info(
            f"✅ Model training complete. "
            f"Metrics: precision={result['metrics'].get('precision', 'N/A'):.4f}, "
            f"recall={result['metrics'].get('recall', 'N/A'):.4f}, "
            f"f1={result['metrics'].get('f1', 'N/A'):.4f}"
        )
        context.add_output_metadata(
            {
                "mlflow_run_id": MetadataValue.text(result.get("run_id", "N/A")),
                "precision": MetadataValue.float(result["metrics"].get("precision", 0.0)),
                "recall": MetadataValue.float(result["metrics"].get("recall", 0.0)),
                "f1_score": MetadataValue.float(result["metrics"].get("f1", 0.0)),
                "model_version": MetadataValue.text(result.get("model_version", "N/A")),
            }
        )
        return result
    except Exception as e:
        context.log.error(f"Model training failed: {e}")
        raise


@asset(
    deps=[streaming_cleaning_asset],
    group_name="streaming_pipeline",
    compute_kind="machine_learning",
    description="Applies ML model inference in real-time and alerts on app-errors topic.",
)
def model_inference_asset(context: AssetExecutionContext):
    """Run ML inference with post-inference quality validation."""
    target = _target_records()
    context.log.info(f"Starting ML inference on clean stream (target {target})...")
    anomalies = run_inference(max_messages=target)
    context.log.info(f"{anomalies} cyber-attacks detected and sent to alert system.")

    # ── DATA QUALITY GATE: Validate inference output ──
    project_root = get_project_root()
    export_path = os.path.join(project_root, "data", "exports", "app_errors.jsonl")
    if os.path.exists(export_path):
        records = []
        with open(export_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        if records:
            try:
                report = validate_inference_output(records, total_processed=target or 0)
                context.log.info(
                    f"✅ Inference output quality PASSED "
                    f"({report.passed_rules}/{report.total_rules} rules passed)"
                )
            except DataQualityError as e:
                context.log.error("❌ Inference output quality FAILED")
                context.log.error(e.report.summary())
                raise

    context.add_output_metadata(
        {
            "anomalies_detected": MetadataValue.int(anomalies),
            "export_path": MetadataValue.path("data/exports/app_errors.jsonl"),
        }
    )
    return anomalies
