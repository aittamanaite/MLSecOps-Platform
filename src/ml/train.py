"""Model training pipeline for network anomaly detection.

Trains an XGBoost classifier on preprocessed CICIDS2017 feature data,
ensuring strict prevention of data leakage by stripping identifiers and 
sensitive fields prior to Train/Test splitting and Cross-Validation.
Includes sample weighting based on fine-grained attack labels to handle rare attack types.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.utils.class_weight import compute_sample_weight
import xgboost as xgb

from src.ml.features import FEATURE_NAMES, SENSITIVE_COLUMNS_TO_DROP, extract_features, extract_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Returns absolute path to project root."""
    return Path(__file__).resolve().parent.parent.parent


def sanitize_and_prepare_data(
    df_raw: pd.DataFrame,
) -> Tuple[pd.DataFrame, np.ndarray, pd.Series]:
    """Strips sensitive/leaky columns and prepares X, y, and granular labels.

    Args:
        df_raw: Raw input DataFrame containing a 'label' column.

    Returns:
        Tuple of (X DataFrame, y binary array, granular_labels Series).
    """
    logger.info("Sanitizing input data to prevent Data Leakage...")

    # Preserve multi-class granular label column for sample weight calculations
    granular_labels = df_raw["label"] if "label" in df_raw.columns else None

    # Extract binary target label vector
    y = extract_labels(df_raw)

    # Sanitize and extract only the non-leaky numerical feature subset
    X = extract_features(df_raw)

    # Double-check: Ensure no sensitive column bypassed feature extraction
    leaked = [col for col in SENSITIVE_COLUMNS_TO_DROP if col in X.columns]
    if leaked:
        logger.warning(f"Detected leaked columns in feature set! Dropping immediately: {leaked}")
        X.drop(columns=leaked, inplace=True, errors="ignore")

    logger.info(f"Features prepared successfully. Matrix shape: {X.shape}, Target distribution: {np.bincount(y)}")
    return X, y, granular_labels


def compute_dampened_sample_weights(granular_labels: pd.Series) -> np.ndarray:
    """Computes square-root dampened sample weights from multi-class labels.

    Args:
        granular_labels: Series containing multi-class category strings (e.g. 'DDoS', 'PortScan').

    Returns:
        Numpy array of per-sample weights.
    """
    # Calculate balanced weights per fine-grained label class
    balanced_weights = compute_sample_weight(class_weight="balanced", y=granular_labels)
    # Apply square-root dampening so extreme rare attack weights do not cause instability
    dampened_weights = np.sqrt(balanced_weights)
    return dampened_weights


def evaluate_with_cross_validation(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    sample_weight_train: Optional[np.ndarray] = None,
    n_splits: int = 5,
    random_state: int = 42,
) -> Dict[str, float]:
    """Runs Stratified K-Fold Cross-Validation on training data using sample weights."""
    logger.info(f"Starting {n_splits}-Fold Stratified Cross-Validation...")
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    f1_scores, precision_scores, recall_scores, accuracy_scores = [], [], [], []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
        X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
        y_cv_train, y_cv_val = y_train[train_idx], y_train[val_idx]
        
        sw_cv_train = sample_weight_train[train_idx] if sample_weight_train is not None else None

        model_cv = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=random_state,
            eval_metric="logloss",
            n_jobs=-1,
        )
        model_cv.fit(X_cv_train, y_cv_train, sample_weight=sw_cv_train)

        preds = model_cv.predict(X_cv_val)

        accuracy_scores.append(accuracy_score(y_cv_val, preds))
        precision_scores.append(precision_score(y_cv_val, preds, zero_division=0))
        recall_scores.append(recall_score(y_cv_val, preds, zero_division=0))
        f1_scores.append(f1_score(y_cv_val, preds, zero_division=0))

    cv_metrics = {
        "cv_mean_accuracy": float(np.mean(accuracy_scores)),
        "cv_mean_precision": float(np.mean(precision_scores)),
        "cv_mean_recall": float(np.mean(recall_scores)),
        "cv_mean_f1": float(np.mean(f1_scores)),
    }

    logger.info(
        f"Cross-Validation Completed. Mean CV F1-Score: {cv_metrics['cv_mean_f1']:.4f}, Mean Accuracy: {cv_metrics['cv_mean_accuracy']:.4f}"
    )
    return cv_metrics


def train_model(
    data_path: Optional[str] = None,
    test_size: float = 0.2,
    random_state: int = 42,
    save_local: bool = True,
) -> Tuple[Any, Dict[str, float]]:
    """Executes full training pipeline with sample weighting and MLflow tracking."""
    # 1. Load Raw Data
    if data_path is None:
        data_path = get_project_root() / "data" / "exports" / "dataset.parquet"
    else:
        data_path = Path(data_path)

    if not data_path.exists():
        logger.error(f"Dataset file not found at: {data_path}")
        raise FileNotFoundError(f"Dataset file not found at: {data_path}")

    logger.info(f"Loading raw dataset from {data_path}...")
    if data_path.suffix == ".parquet":
        df_raw = pd.read_parquet(data_path)
    else:
        df_raw = pd.read_csv(data_path)

    # 2. Sanitize Data & Extract Multi-Class Labels
    X, y, granular_labels = sanitize_and_prepare_data(df_raw)

    # 3. Compute Sample Weights from Granular Class Labels
    if granular_labels is not None:
        logger.info("Computing square-root dampened class weights from 'label' column...")
        sample_weights = compute_dampened_sample_weights(granular_labels)
    else:
        logger.warning("'label' column missing; proceeding without sample weights.")
        sample_weights = np.ones(len(y))

    # 4. Train / Test Split (splitting X, y, and sample_weights together)
    X_train, X_test, y_train, y_test, sw_train, sw_test = train_test_split(
        X, y, sample_weights, test_size=test_size, random_state=random_state, stratify=y
    )
    logger.info(f"Data split into Train ({len(X_train)}) and Test hold-out ({len(X_test)}).")

    # MLflow Setup
    try:
        import mlflow
        import mlflow.xgboost

        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("network-anomaly-detection")
        mlflow_enabled = True
    except Exception as e:
        logger.warning(f"MLflow initialization failed: {e}. Training without MLflow tracking.")
        mlflow_enabled = False

    # 5. Perform Cross-Validation on X_train with sw_train
    cv_metrics = evaluate_with_cross_validation(
        X_train, y_train, sample_weight_train=sw_train, n_splits=5, random_state=random_state
    )

    # 6. Train Final XGBoost Classifier
    logger.info("Training final XGBoost classifier with sample weights...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=random_state,
        eval_metric="logloss",
        n_jobs=-1,
    )

    if mlflow_enabled:
        mlflow.start_run(run_name="xgboost_weighted_training")
        mlflow.log_params(
            {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1,
                "sample_weighting": True,
                "features_count": X.shape[1],
            }
        )

    model.fit(X_train, y_train, sample_weight=sw_train)

    # 7. Evaluate on Unseen Hold-out Test Set
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    test_metrics = {
        "test_accuracy": float(accuracy_score(y_test, y_pred)),
        "test_precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "test_recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "test_f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "test_roc_auc": float(roc_auc_score(y_test, y_proba)),
    }

    all_metrics = {**cv_metrics, **test_metrics}

    logger.info("Final Test Evaluation Metrics:")
    for k, v in test_metrics.items():
        logger.info(f"  {k}: {v:.4f}")

    if mlflow_enabled:
        mlflow.log_metrics(all_metrics)
        mlflow.xgboost.log_model(model, artifact_path="model")
        mlflow.end_run()

    # 8. Save Model Locally
    if save_local:
        artifact_dir = get_project_root() / "src" / "ml" / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        model_file = artifact_dir / "model.joblib"
        joblib.dump(model, model_file)
        logger.info(f"Model artifact saved successfully to {model_file}")

    return model, all_metrics


if __name__ == "__main__":
    train_model()
