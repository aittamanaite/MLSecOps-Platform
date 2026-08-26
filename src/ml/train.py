"""Model training script for network anomaly detection.

Trains an IsolationForest model on CICIDS2017 network traffic logs
and logs metrics and artifacts to MLflow.
"""

import os
import json
import logging
import time
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, f1_score, accuracy_score
import joblib

try:
    import mlflow
    import mlflow.sklearn
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

from src.ml.features import extract_features, extract_labels, preprocess_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_project_root() -> str:
    """Get the root directory of the project."""
    # Assuming this script is in src/ml/train.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))

def load_training_data(data_path: str = None) -> list:
    """Load cleaned records from JSONL file.
    
    Args:
        data_path: Path to the data file. Defaults to data/exports/cleaned_logs.jsonl.
        
    Returns:
        List of dictionaries containing log records.
    """
    if data_path is None:
        data_path = os.path.join(get_project_root(), "data", "exports", "cleaned_logs.jsonl")
        
    if not os.path.exists(data_path):
        logger.error(f"Data file not found: {data_path}")
        return []
        
    records = []
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        logger.info(f"Loaded {len(records)} records from {data_path}")
    except Exception as e:
        logger.error(f"Error loading training data: {e}")
        
    return records

def train_model(records: list, contamination: float = 0.1, n_estimators: int = 200, random_state: int = 42) -> dict:
    """Train Isolation Forest model.
    
    Args:
        records: List of dictionaries.
        contamination: The proportion of outliers in the data set.
        n_estimators: The number of base estimators in the ensemble.
        random_state: Controls the pseudo-randomness of the selection.
        
    Returns:
        Dictionary with run_id, metrics, and model_version.
    """
    if not records:
        logger.error("No records provided for training.")
        return {}
        
    logger.info("Extracting features and labels...")
    df_features = extract_features(records)
    y_true = extract_labels(records)
    
    # Split the data into train and test sets (80/20)
    logger.info("Splitting data into train and test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        df_features, y_true, test_size=0.2, random_state=random_state, stratify=y_true
    )
    
    logger.info("Preprocessing features...")
    X_train_scaled, scaler = preprocess_features(X_train, fit=True)
    X_test_scaled, _ = preprocess_features(X_test, scaler=scaler, fit=False)
    
    logger.info(f"Training RandomForestClassifier (n_estimators={n_estimators})...")
    start_time = time.time()
    
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    model.fit(X_train_scaled, y_train)
    train_time = time.time() - start_time
    logger.info(f"Training completed in {train_time:.2f} seconds.")
    
    # Evaluate on the TEST set to prevent data leakage/overfitting
    y_pred_mapped = model.predict(X_test_scaled)
    
    precision = float(precision_score(y_test, y_pred_mapped, zero_division=0))
    recall = float(recall_score(y_test, y_pred_mapped, zero_division=0))
    f1 = float(f1_score(y_test, y_pred_mapped, zero_division=0))
    accuracy = float(accuracy_score(y_test, y_pred_mapped))
    
    logger.info(f"Metrics - Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}, Accuracy: {accuracy:.4f}")
    
    metrics = {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "training_duration_seconds": train_time
    }
    
    params = {
        "contamination": contamination,
        "n_estimators": n_estimators,
        "random_state": random_state,
        "n_features": X_train_scaled.shape[1],
        "n_samples": X_train_scaled.shape[0]
    }
    
    # Save artifacts locally
    artifacts_dir = os.path.join(get_project_root(), "src", "ml", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    model_path = os.path.join(artifacts_dir, "model.joblib")
    scaler_path = os.path.join(artifacts_dir, "scaler.joblib")
    
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    logger.info(f"Saved model and scaler locally in {artifacts_dir}")
    
    result = {
        "metrics": metrics,
        "run_id": None,
        "model_version": None
    }
    
    # MLflow logging
    if MLFLOW_AVAILABLE:
        try:
            tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment("mlsecops-anomaly-detection")
            
            # MLflow configuration
            # System metrics and autologging are disabled to prevent container hang issues
            
            with mlflow.start_run() as run:
                # 1. Description
                mlflow.set_tag("mlflow.note.content", 
                    "# 🛡️ Network Anomaly Detection\n\n"
                    "**Purpose**: Detect cyber-attacks in real-time streaming traffic.\n\n"
                    "**Model**: `RandomForestClassifier` (Supervised)\n\n"
                    "**Dataset**: CICIDS2017\n\n"
                    "**Preprocessing**: `StandardScaler` (fitted on 80% train split to avoid data leakage).\n\n"
                    "**Evaluation**: Strict 20% holdout test set."
                )
                
                # 2. Tags
                mlflow.set_tags({
                    "model_type": "Random Forest",
                    "dataset": "CICIDS2017",
                    "environment": "development",
                    "pipeline": "streaming",
                    "task": "anomaly_detection"
                })
                
                # 3. Parameters
                # Add additional parameters beyond the model hyperparams
                params.update({
                    "test_split_ratio": 0.2,
                    "stratification": "True",
                    "scaler_type": "StandardScaler",
                    "class_weight": "balanced"
                })
                mlflow.log_params(params)
                
                # 4. Metrics
                mlflow.log_metrics(metrics)
                
                # Log model
                mlflow.sklearn.log_model(
                    sk_model=model,
                    artifact_path="random_forest_model",
                    registered_model_name="network-anomaly-detector"
                )
                
                # Create and log classification report and confusion matrix as artifacts
                report_str = classification_report(y_test, y_pred_mapped)
                report_path = os.path.join(artifacts_dir, "classification_report.txt")
                with open(report_path, "w") as f:
                    f.write(report_str)
                mlflow.log_artifact(report_path, "evaluation")
                
                cm = confusion_matrix(y_test, y_pred_mapped).tolist()
                cm_path = os.path.join(artifacts_dir, "confusion_matrix.json")
                with open(cm_path, "w") as f:
                    json.dump(cm, f, indent=2)
                mlflow.log_artifact(cm_path, "evaluation")
                
                # Log scaler as artifact
                mlflow.log_artifact(scaler_path, "scaler")
                
                run_id = run.info.run_id
                logger.info(f"Logged to MLflow (run_id: {run_id})")
                result["run_id"] = run_id
        except Exception as e:
            logger.warning(f"Failed to log to MLflow: {e}. Artifacts are still saved locally.")
    else:
        logger.warning("MLflow not installed. Skipping MLflow tracking.")
        
    return result

def run_training(data_path: str = None, contamination: float = 0.1, n_estimators: int = 200) -> dict:
    """Orchestrator function to load data and train model."""
    logger.info("Starting training pipeline...")
    records = load_training_data(data_path)
    return train_model(records, contamination=contamination, n_estimators=n_estimators)

if __name__ == "__main__":
    run_training()
