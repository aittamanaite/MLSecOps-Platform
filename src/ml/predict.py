"""Inference module for network anomaly detection.

Loads the trained XGBoost model (via MLflow or local fallback) and executes 
single-record or batch predictions without feature scaling.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from src.ml.features import FEATURE_NAMES, preprocess_features

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Returns the absolute root directory of the project."""
    return Path(__file__).resolve().parent.parent.parent


def load_model(model_path: Optional[str] = None) -> Any:
    """Loads the trained model from MLflow registry or local artifact fallback.

    Args:
        model_path: Optional local path to model.joblib.

    Returns:
        Loaded model object, or None if no model could be loaded.
    """
    model = None

    # 1. Try loading from MLflow Registry
    try:
        import mlflow
        import mlflow.xgboost

        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow.set_tracking_uri(tracking_uri)

        # Try Production stage first
        model_uri = "models:/network-anomaly-detector-xgboost/Production"
        try:
            model = mlflow.xgboost.load_model(model_uri)
            logger.info(f"Successfully loaded model from MLflow: {model_uri}")
        except Exception:
            # Fall back to latest version
            model_uri = "models:/network-anomaly-detector-xgboost/latest"
            try:
                model = mlflow.xgboost.load_model(model_uri)
                logger.info(f"Successfully loaded model from MLflow: {model_uri}")
            except Exception as e:
                logger.debug(f"Could not load model from MLflow registry: {e}")

    except ImportError:
        logger.debug("MLflow package not available.")
    except Exception as e:
        logger.debug(f"Error accessing MLflow server: {e}")

    # 2. Fall back to local artifact
    if model is None:
        if model_path is None:
            model_path = get_project_root() / "src" / "ml" / "artifacts" / "model.joblib"
        else:
            model_path = Path(model_path)

        if model_path.exists():
            try:
                model = joblib.load(model_path)
                logger.info(f"Successfully loaded local model from: {model_path}")
            except Exception as e:
                logger.error(f"Error loading local model file: {e}")
        else:
            logger.error(f"Local model file not found at: {model_path}")

    return model


def predict(record: Dict[str, Any], model: Any = None) -> Tuple[str, float]:
    """Predicts whether a single network flow record is an anomaly (ATTACK or BENIGN).

    Args:
        record: Dictionary containing flow features.
        model: Loaded model instance. If None, attempts to load default model.

    Returns:
        Tuple of (label: "ATTACK" | "BENIGN", confidence_score: float)
    """
    if model is None:
        model = load_model()
        if model is None:
            logger.error("No model available to execute prediction.")
            return "BENIGN", 0.0

    try:
        # Convert dictionary to single-row DataFrame and align features
        df_raw = pd.DataFrame([record])
        df_features = preprocess_features(df_raw)

        # Execute prediction
        pred_code = int(model.predict(df_features)[0])
        label = "ATTACK" if pred_code == 1 else "BENIGN"

        # Calculate confidence score via predict_proba
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(df_features)[0]
            confidence = float(proba[pred_code])
        else:
            confidence = 1.0

        return label, confidence

    except Exception as e:
        logger.error(f"Error executing prediction on record: {e}")
        return "BENIGN", 0.0


def predict_batch(records: List[Dict[str, Any]], model: Any = None) -> List[Dict[str, Any]]:
    """Vectorized batch prediction for multiple flow records.

    Args:
        records: List of feature dictionaries.
        model: Loaded model instance.

    Returns:
        List of prediction dicts: [{"is_anomaly": "ATTACK" | "BENIGN", "confidence": float}, ...]
    """
    if not records:
        return []

    if model is None:
        model = load_model()
        if model is None:
            logger.error("No model available to execute batch prediction.")
            return [{"is_anomaly": "BENIGN", "confidence": 0.0} for _ in records]

    try:
        # Convert list of dicts to DataFrame and preprocess
        df_raw = pd.DataFrame(records)
        df_features = preprocess_features(df_raw)

        predictions = model.predict(df_features)

        # Get probabilities if supported
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(df_features)
            results = [
                {
                    "is_anomaly": "ATTACK" if pred == 1 else "BENIGN",
                    "confidence": float(probabilities[i][pred]),
                }
                for i, pred in enumerate(predictions)
            ]
        else:
            results = [
                {
                    "is_anomaly": "ATTACK" if pred == 1 else "BENIGN",
                    "confidence": 1.0,
                }
                for pred in predictions
            ]

        return results

    except Exception as e:
        logger.error(f"Error executing batch prediction: {e}")
        return [{"is_anomaly": "BENIGN", "confidence": 0.0} for _ in records]