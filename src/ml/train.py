"""Model training pipeline for network anomaly detection.

Trains an XGBoost classifier on preprocessed CICIDS2017 feature data,
ensuring strict prevention of data leakage by stripping identifiers and 
sensitive fields prior to Train/Test splitting and Cross-Validation.
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
import xgboost as xgb

from src.ml.features import FEATURE_NAMES, SENSITIVE_COLUMNS_TO_DROP, extract_features, extract_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Returns absolute path to project root."""
    return Path(__file__).resolve().parent.parent.parent


def sanitize_and_prepare_data(
    df_raw: pd.DataFrame,
) -> Tuple[pd.DataFrame, np.ndarray]:
    """Strips sensitive/leaky columns and prepares X and y.

    Preventing Data Leakage:
    - Removes all identifiers (IPs, Ports, Timestamps, Flow IDs).
    - Separates target labels before cross-validation.

    Args:
        df_raw: Raw input DataFrame.

    Returns:
        Tuple of (X DataFrame containing only FEATURE_NAMES, y target labels array).
    """
    logger.info("Sanitizing input data to prevent Data Leakage...")

    # Extract target label vector first
    y = extract_labels(df_raw)

    # Sanitize and extract only the non-leaky numerical feature subset
    X = extract_features(df_raw)

    # Double-check: Ensure no sensitive column bypassed feature extraction
    leaked = [col for col in SENSITIVE_COLUMNS_TO_DROP if col in X.columns]
    if leaked:
        logger.warning(f"Detected leaked columns in feature set! Dropping immediately: {leaked}")
        X.drop(columns=leaked, inplace=True, errors="ignore")

    logger.info(f"Features prepared successfully. Matrix shape: {X.shape}, Target distribution: {np.bincount(y)}")
    return X, y


def evaluate_with_cross_validation(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    n_splits: int = 5,
    random_state: int = 42,
) -> Dict[str, float]:
    """Runs Stratified K-Fold Cross-Validation on training data.

    Args:
        X_train: Training feature set (sanitized).
        y_train: Training labels.
        n_splits: Number of CV folds.
        random_state: Random state seed.

    Returns:
        Dictionary containing mean cross-validation metrics.
    """
    logger.info(f"Starting {n_splits}-Fold Stratified Cross-Validation...")
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    f1_scores, precision_scores, recall_scores, accuracy_scores = [], [], [], []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
        X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
        y_cv_train, y_cv_val = y_train[train_idx], y_train[val_idx]

        model_cv = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=random_state,
            eval_metric="logloss",
            n_jobs=-1,
        )
        model_cv.fit(X_cv_train, y_cv_train)

        preds = model_cv.predict(X_cv_val)

        accuracy_scores.append(accuracy_score(y_cv_val, preds))
        precision_scores.append(precision_score(y_cv_val, preds, zero_division=0))
        recall_scores.append(recall_score(y_cv_val, preds, zero_division=0))
        f1_scores.append(f1_score(y_cv_val, preds, zero_division=0))

        logger.debug(f"Fold {fold} - Accuracy: {accuracy_scores[-1]:.4f}, F1: {f1_scores[-1]:.4f}")

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
    """Executes full training pipeline with MLflow tracking and leak prevention.

    Args:
        data_path: Path to raw dataset CSV/Parquet.
        test_size: Fraction of data for final testing hold-out.
        random_state: Seed for reproducibility.
        save_local: Whether to save model.joblib locally in artifacts.

    Returns:
        Tuple of (trained_model, eval_metrics)
    """
    # 1. Load Raw Data
    if data_path is None:
        data_path = get_project_root() / "data" / "raw" / "dataset.csv"
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

    # 2. Sanitize and Drop Sensitive/Leaky Features BEFORE Splitting/CV
    X, y = sanitize_and_prepare_data(df_raw)

    # 3. Train / Test Hold-out Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
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

    # 4. Perform Cross-Validation (on X_train only)
    cv_metrics = evaluate_with_cross_validation(X_train, y_train, n_splits=5, random_state=random_state)

    # 5. Train Final Model on full X_train
    logger.info("Training final XGBoost classifier...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=random_state,
        eval_metric="logloss",
        n_jobs=-1,
    )

    if mlflow_enabled:
        mlflow.start_run(run_name="xgboost_leak_free_training")
        mlflow.log_params(
            {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1,
                "features_count": X.shape[1],
                "scaler_used": False,
            }
        )

    model.fit(X_train, y_train)

    # 6. Evaluate on Unseen Hold-out Test Set
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

    logger.info(f"Final Test Evaluation Metrics:")
    for k, v in test_metrics.items():
        logger.info(f"  {k}: {v:.4f}")

    if mlflow_enabled:
        mlflow.log_metrics(all_metrics)
        mlflow.xgboost.log_model(model, artifact_path="model")
        mlflow.end_run()

    # 7. Save model locally if required
    if save_local:
        artifact_dir = get_project_root() / "src" / "ml" / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        model_file = artifact_dir / "model.joblib"
        joblib.dump(model, model_file)
        logger.info(f"Model artifact saved successfully to {model_file}")

    return model, all_metrics


if __name__ == "__main__":
    train_model()