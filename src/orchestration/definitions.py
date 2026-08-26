"""Dagster definitions for the MLSecOps platform.

Assembles assets, jobs, sensors, and schedules into a single Definitions object.
"""

import os
import glob
import json
import hashlib
from datetime import datetime

from dagster import (
    sensor,
    SensorEvaluationContext,
    RunRequest,
    SkipReason,
    Definitions,
    define_asset_job,
    ScheduleDefinition,
    AssetSelection,
)

from src.orchestration.assets import (
    streaming_ingestion_asset,
    streaming_cleaning_asset,
    model_inference_asset,
    model_training_asset,
)

# ==========================================
# 1. Job Definitions
# ==========================================

# Streaming pipeline: Ingest -> Clean -> Inference
streaming_pipeline_job = define_asset_job(
    name="realtime_mlsecops_job",
    selection=AssetSelection.assets(
        streaming_ingestion_asset,
        streaming_cleaning_asset,
        model_inference_asset,
    ),
)

# ML Training pipeline: Clean -> Train
ml_training_job = define_asset_job(
    name="ml_training_job",
    selection=AssetSelection.assets(model_training_asset),
)

# Full pipeline: Ingest -> Clean -> Train + Inference
full_pipeline_job = define_asset_job(
    name="full_mlsecops_pipeline_job",
    selection=AssetSelection.assets(
        streaming_ingestion_asset,
        streaming_cleaning_asset,
        model_training_asset,
        model_inference_asset,
    ),
)

# ==========================================
# 2. Sensor
# ==========================================

@sensor(
    name="csv_streaming_sensor",
    job=streaming_pipeline_job,
    minimum_interval_seconds=30,
)
def csv_streaming_sensor(context: SensorEvaluationContext):
    """
    Monitor data/raw/ for new or modified CSV files.
    Triggers a streaming micro-batch cycle on changes.
    """
    data_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/raw")
    )
    if not os.path.exists(data_dir):
        yield SkipReason("Data directory data/raw/ does not exist.")
        return

    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not csv_files:
        yield SkipReason("No CSV files found in data/raw/.")
        return

    current_state = {}
    for filepath in csv_files:
        try:
            stats = os.stat(filepath)
            current_state[os.path.basename(filepath)] = (
                f"{stats.st_mtime}_{stats.st_size}"
            )
        except Exception as e:
            context.log.warning(f"Cannot stat {filepath}: {e}")

    last_state_str = context.cursor or "{}"
    try:
        last_state = json.loads(last_state_str)
    except Exception:
        last_state = {}

    if current_state != last_state:
        context.update_cursor(json.dumps(current_state))
        # Deterministic run key based on state hash (prevents duplicate runs)
        state_hash = hashlib.md5(
            json.dumps(current_state, sort_keys=True).encode()
        ).hexdigest()[:12]
        context.log.info(
            "New/modified CSV files detected in data/raw/. "
            "Launching streaming pipeline..."
        )
        yield RunRequest(
            run_key=f"streaming_run_{state_hash}",
        )
    else:
        yield SkipReason("No file modifications detected in data/raw/.")


# ==========================================
# 3. Schedules
# ==========================================

hourly_streaming_schedule = ScheduleDefinition(
    name="hourly_streaming_schedule",
    job=streaming_pipeline_job,
    cron_schedule="0 * * * *",
)

# ==========================================
# 4. Definitions Assembly
# ==========================================

defs = Definitions(
    assets=[
        streaming_ingestion_asset,
        streaming_cleaning_asset,
        model_training_asset,
        model_inference_asset,
    ],
    jobs=[streaming_pipeline_job, ml_training_job, full_pipeline_job],
    schedules=[hourly_streaming_schedule],
    sensors=[csv_streaming_sensor],
)
