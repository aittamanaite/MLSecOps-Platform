import os
import glob
import json
import logging
from datetime import datetime
from dagster import (
    sensor, 
    SensorEvaluationContext, 
    RunRequest, 
    Definitions, 
    define_asset_job, 
    ScheduleDefinition,
    AssetSelection
)

# Importation des nouveaux Assets du pipeline Streaming
from src.orchestration.assets import (
    streaming_ingestion_asset,
    streaming_cleaning_asset,
    model_inference_asset
)

# ==========================================
# 1. Définition du Job Principal (Streaming Micro-Batch)
# ==========================================
# Exécute l'Ingestion (Producer) -> Nettoyage (Cleaner) -> Inférence (Model)
streaming_pipeline_job = define_asset_job(
    name="realtime_mlsecops_job",
    selection=(
        AssetSelection.assets(streaming_ingestion_asset) 
        | AssetSelection.assets(streaming_cleaning_asset)
        | AssetSelection.assets(model_inference_asset)
    )
)

# ==========================================
# 2. Définition du Sensor 
# ==========================================
@sensor(
    name="csv_streaming_sensor",
    job=streaming_pipeline_job,
    minimum_interval_seconds=30
)
def csv_streaming_sensor(context: SensorEvaluationContext):
    """
    Surveille le répertoire local data/raw/.
    S'il y a de nouveaux fichiers, il déclenche un cycle (micro-batch) 
    d'ingestion, de nettoyage et d'inférence ML.
    """
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw"))
    if not os.path.exists(data_dir):
        return
        
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    
    current_state = {}
    for filepath in csv_files:
        try:
            stats = os.stat(filepath)
            current_state[os.path.basename(filepath)] = f"{stats.st_mtime}_{stats.st_size}"
        except Exception as e:
            context.log.warning(f"Impossible d'accéder aux statistiques de {filepath} : {e}")

    last_state_str = context.cursor or "{}"
    try:
        last_state = json.loads(last_state_str)
    except Exception:
        last_state = {}

    if current_state != last_state:
        context.update_cursor(json.dumps(current_state))
        context.log.info("Nouveaux fichiers locaux détectés dans data/raw/. Lancement du traitement Streaming...")
        
        yield RunRequest(
            run_key=f"streaming_run_{datetime.now().timestamp()}",
            message="Changement détecté dans data/raw/, lancement du micro-batch streaming."
        )

# Planification optionnelle de sécurité (Toutes les heures par exemple)
hourly_streaming_schedule = ScheduleDefinition(
    name="hourly_streaming_schedule",
    job=streaming_pipeline_job,
    cron_schedule="0 * * * *", 
)

# ==========================================
# 3. Assemblage global des Definitions
# ==========================================
defs = Definitions(
    assets=[
        streaming_ingestion_asset, 
        streaming_cleaning_asset, 
        model_inference_asset
    ],
    jobs=[streaming_pipeline_job],
    schedules=[hourly_streaming_schedule],
    sensors=[csv_streaming_sensor],
)
