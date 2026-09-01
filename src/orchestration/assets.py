<<<<<<< HEAD
from dagster import asset, AssetExecutionContext
from src.streaming.producer import run_producer, get_project_root
from src.streaming.cleaner import run_cleaner
from src.streaming.inference import run_inference
from src.quality.data_quality import (
    validate_raw_csv,
    validate_cleaned_records,
    validate_inference_output,
    DataQualityError,
)
import json
import os
import glob
import pandas as pd
=======
import os

from dagster import asset, AssetExecutionContext, MetadataValue

from src.streaming.producer import run_producer
from src.streaming.cleaner import run_cleaner
from src.streaming.inference import run_inference


def _target_records() -> int:
    """Objectif de volume par micro-batch (surchargeable via STREAM_MAX_RECORDS)."""
    return int(os.getenv("STREAM_MAX_RECORDS", "120000"))


def _read_batch_size() -> int:
    return int(os.getenv("PRODUCER_BATCH_SIZE", "5000"))


def _chunk_stride() -> int:
    """1 = flux séquentiel; >1 = échantillon étalé sur toute la journée (plus d'attaques)."""
    return max(1, int(os.getenv("PRODUCER_CHUNK_STRIDE", "1")))

>>>>>>> 6c556c4 (Initial commit)

@asset(
    group_name="streaming_pipeline",
    compute_kind="python",
    description="Simule le flux réseau en temps réel en envoyant les CSV locaux vers Redpanda (raw-logs)."
)
def streaming_ingestion_asset(context: AssetExecutionContext):
<<<<<<< HEAD
    context.log.info("Lancement de l'ingestion temps réel vers Kafka/Redpanda...")

    # ── DATA QUALITY GATE: Validate raw CSV files before ingestion ──
    project_root = get_project_root()
    data_dir = os.path.join(project_root, "data", "raw")
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))

    for filepath in csv_files:
        context.log.info(f"Quality check on: {os.path.basename(filepath)}")
        df = pd.read_csv(filepath, keep_default_na=False, nrows=10000)
        try:
            report = validate_raw_csv(df)
            context.log.info(
                f"✅ Raw data quality PASSED for {os.path.basename(filepath)} "
                f"({report.passed_rules}/{report.total_rules} rules passed)"
            )
        except DataQualityError as e:
            context.log.error(
                f"❌ Raw data quality FAILED for {os.path.basename(filepath)}"
            )
            context.log.error(e.report.summary())
            raise

    events_published = run_producer(batch_size=1500)
    context.log.info(f"{events_published} événements poussés dans le flux brut.")
    # Structured materialization metadata for easier debugging and plotting
    context.log.info("materialization", extra={"events_published": events_published})
    return events_published

=======
    target = _target_records()
    context.log.info(f"Lancement de l'ingestion temps réel vers Kafka/Redpanda (objectif {target} événements)...")
    events_published = run_producer(
        batch_size=_read_batch_size(),
        max_records=target,
        chunk_stride=_chunk_stride(),
    )
    context.log.info(f"{events_published} événements poussés dans le flux brut.")
    context.add_output_metadata(
        {
            "events_published": MetadataValue.int(events_published),
            "target_records": MetadataValue.int(target),
        }
    )
    return events_published


>>>>>>> 6c556c4 (Initial commit)
@asset(
    deps=[streaming_ingestion_asset],
    group_name="streaming_pipeline",
    compute_kind="python",
    description="Consomme le flux brut, le nettoie et le publie sur cleaned-logs."
)
def streaming_cleaning_asset(context: AssetExecutionContext):
<<<<<<< HEAD
    context.log.info("Lancement du processeur de nettoyage de flux...")
    cleaned = run_cleaner(max_messages=1500)
    context.log.info(f"{cleaned} événements nettoyés et publiés.")

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

    context.log.info("materialization", extra={"events_cleaned": cleaned})
    return cleaned

=======
    target = _target_records()
    context.log.info(f"Lancement du processeur de nettoyage de flux (objectif {target} événements)...")
    cleaned = run_cleaner(max_messages=target)
    context.log.info(f"{cleaned} événements nettoyés et publiés.")
    context.add_output_metadata(
        {
            "events_cleaned": MetadataValue.int(cleaned),
            "export_path": MetadataValue.path("data/exports/cleaned_logs.jsonl"),
        }
    )
    return cleaned


>>>>>>> 6c556c4 (Initial commit)
@asset(
    deps=[streaming_cleaning_asset],
    group_name="streaming_pipeline",
    compute_kind="machine_learning",
    description="Applique le modèle d'IA en temps réel et alerte sur le topic app-errors."
)
def model_inference_asset(context: AssetExecutionContext):
<<<<<<< HEAD
    context.log.info("Lancement de l'inférence du Modèle ML sur le flux propre...")
    anomalies = run_inference(max_messages=1500)
    context.log.info(f"{anomalies} cyber-attaques détectées et envoyées au système d'alerte.")

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
        try:
            report = validate_inference_output(records, total_processed=1500)
            context.log.info(
                f"✅ Inference output quality PASSED "
                f"({report.passed_rules}/{report.total_rules} rules passed)"
            )
        except DataQualityError as e:
            context.log.error("❌ Inference output quality FAILED")
            context.log.error(e.report.summary())
            raise

    context.log.info("materialization", extra={"anomalies_detected": anomalies})
=======
    target = _target_records()
    context.log.info(f"Lancement de l'inférence du Modèle ML sur le flux propre (objectif {target})...")
    anomalies = run_inference(max_messages=target)
    context.log.info(f"{anomalies} cyber-attaques détectées et envoyées au système d'alerte.")
    context.add_output_metadata(
        {
            "anomalies_detected": MetadataValue.int(anomalies),
            "export_path": MetadataValue.path("data/exports/app_errors.jsonl"),
        }
    )
>>>>>>> 6c556c4 (Initial commit)
    return anomalies
