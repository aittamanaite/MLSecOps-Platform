# Machine Learning Module (`src/ml/`)

This directory contains the core machine-learning pipeline for the cybersecurity anomaly-detection platform. It ingests sanitized network-flow feature data derived from the **CICIDS2017** dataset, executes **Stratified K-Fold Cross-Validation**, trains an **XGBoost** classifier with strict **Data Leakage prevention**, and serves real-time inference backed by **MLflow** experiment tracking.

> **Navigation tip:** If you landed here directly, read the root [`README.md`](../../README.md), [`src/README.md`](../README.md), and [`app/readme.md`](../../app/readme.md) to understand how this module fits into the broader streaming architecture.

---

## Files Overview

| File | What it does |
| :--- | :--- |
| `__init__.py` | Package marker; makes `src.ml` importable. |
| `features.py` | Canonical feature schema (`FEATURE_NAMES`), sensitive column drop lists, and sanitization/extraction utilities. |
| `train.py` | Sanitizes data, executes Cross-Validation, trains the XGBoost model, logs metrics/artifacts to MLflow, and saves local binaries. |
| `predict.py` | Loads the trained model (MLflow registry or local fallback) and executes single/batch inference. |

---

## 1. `features.py` — Feature Engineering & Sanitization

### Feature Definition
Exposes the canonical feature schema expected by the model. Sensitive identifier fields (such as `IP addresses`, `Port numbers`, `Timestamps`, and `Flow IDs`) are explicitly flagged for removal to prevent **Data Leakage**.

### Preprocessing Helpers
- **`extract_features(df_or_dicts)`**: Strips sensitive/leaky fields and enforces feature ordering.
- **`extract_labels(df_or_dicts)`**: Safely maps target labels (e.g., `BENIGN` vs `ATTACK` or multi-class mapping) to binary targets (`0` or `1`).

> No feature scaling (e.g., StandardScaler) is applied — XGBoost natively handles unscaled tree-based splitting and missing/infinite values.

---

## 2. `train.py` — Model Training & Leakage Prevention

### Key Highlights:
1. **Strict Data Leakage Guard:** Drops sensitive identifier columns and target labels *before* performing train/test splits or Stratified K-Fold Cross-Validation.
2. **Stratified K-Fold Cross-Validation:** Runs 5-fold cross-validation on `X_train` only to evaluate out-of-fold `Precision`, `Recall`, `F1-Score`, and `Accuracy`.
3. **MLflow Tracking:** Logs parameters (`n_estimators`, `max_depth`, `learning_rate`), metrics (`CV mean scores`, `Test hold-out metrics`), and logs the logged XGBoost model artifact.
4. **Local Fallback Storage:** Saves `model.joblib` to `src/ml/artifacts/` for local runtime execution.

---

## 3. `predict.py` — Inference

### `load_model(model_path=None)`
Attempts to load the Production model from **MLflow** first. If MLflow is unreachable or unconfigured, it seamlessly falls back to `src/ml/artifacts/model.joblib`.

### `predict(record: Dict)` / `predict_batch(records: List[Dict])`
Extracts and orders the features using `features.py`, then runs batch or single-record predictions returning predicted class labels (`ATTACK` or `BENIGN`) alongside prediction confidence probabilities.

---

## How to Train the Model

Ensure your environment dependencies are installed and the processed balanced dataset exists (default location: `data/exports/dataset.parquet` or `data/exports/cleaned_logs.parquet`).

### 1. Standard Execution (Default Paths)
To train the model using default settings and automated file lookup:

```bash
python -m src.ml.train