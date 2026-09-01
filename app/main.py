"""FastAPI Anomaly Detection API.

A FastAPI service that loads a trained XGBoost model at startup and
exposes endpoints for real-time single and batch network anomaly predictions,
health readiness checks, and Prometheus metrics scraping.
"""

from contextlib import asynccontextmanager
import logging
import time
from typing import List, Union

from fastapi import FastAPI, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.models import BatchPredictRequest, FlowItem
from src.ml.predict import load_model, predict, predict_batch

logger = logging.getLogger(__name__)

# Prometheus Metrics
# -------------------------------------------------------------
PREDICTIONS_TOTAL = Counter(
    "model_predictions_total",
    "Total number of predictions made by the model",
    ["model_version"],
)

ANOMALIES_DETECTED = Counter(
    "anomalies_detected_total",
    "Total number of network anomalies detected",
)

MODEL_INFERENCE_TIME = Histogram(
    "model_inference_seconds",
    "Time spent running model inference",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the trained model once at startup; release it on shutdown."""
    model = load_model("src/ml/artifacts/model.joblib")
    app.state.model = model
    yield
    app.state.model = None


app = FastAPI(
    title="Network Anomaly Detection API",
    description="Real-time network security inference engine built on FastAPI & XGBoost",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Readiness probe.

    Returns the service status and whether the model was loaded at startup.
    """
    model_loaded = getattr(app.state, "model", None) is not None
    return {"status": "ok" if model_loaded else "degraded", "model_loaded": model_loaded}


@app.post("/predict")
def predict_network_traffic(record: FlowItem):
    """Predict whether a single network flow is an anomaly.

    Body: a FlowItem JSON object (33 flow features required).
    Returns the anomaly label and a confidence score.
    """
    if getattr(app.state, "model", None) is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded or service is initializing.",
        )

    start_time = time.time()
    try:
        label, confidence = predict(
            record.model_dump(),
            app.state.model,
        )

        PREDICTIONS_TOTAL.labels(model_version="V1.0").inc()
        if label in [1, "ATTACK"]:
            ANOMALIES_DETECTED.inc()

        return {"is_anomaly": label, "confidence": confidence}

    except Exception as e:
        logger.error(f"Error processing single prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error during prediction.")
    finally:
        MODEL_INFERENCE_TIME.observe(time.time() - start_time)


@app.post("/predict/batch")
def predict_batch_network_traffic(records: Union[List[FlowItem], BatchPredictRequest]):
    """Predict anomalies for a batch of network flows.

    Body: either a JSON array of FlowItem objects or
    a BatchPredictRequest object shaped as {"flows": [FlowItem, ...]}.
    Returns per-record predictions plus aggregate counts.
    """
    if getattr(app.state, "model", None) is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded or service is initializing.",
        )

    # Normalize payload shapes into a list of FlowItem
    if isinstance(records, BatchPredictRequest):
        items = records.flows
    else:
        items = records

    if not items:
        raise HTTPException(status_code=422, detail="Batch list cannot be empty.")

    raw_records = [r.model_dump() for r in items]
    logger.info(f"Processing batch prediction for {len(raw_records)} records.")

    start_time = time.time()
    try:
        results = predict_batch(raw_records, app.state.model)
        batch_size = len(results)

        PREDICTIONS_TOTAL.labels(model_version="V1.0").inc(batch_size)

        anomalies_count = sum(
            1 for res in results if res.get("is_anomaly") in ["ATTACK", 1, True]
        )

        if anomalies_count > 0:
            ANOMALIES_DETECTED.inc(anomalies_count)

        return {
            "predictions": results,
            "total_processed": batch_size,
            "anomalies_found": anomalies_count,
        }

    except Exception as e:
        logger.error(f"Error processing batch prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error during batch prediction.")
    finally:
        MODEL_INFERENCE_TIME.observe(time.time() - start_time)


@app.get("/metrics")
async def get_metrics():
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)