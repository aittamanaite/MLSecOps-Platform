# Machine Learning Module (`src/ml/`)

This directory contains the machine-learning pipeline for the
cybersecurity anomaly-detection platform. It ingests network-flow data
derived from the **CICIDS2017** dataset, engineers features, trains an
**XGBoost** cost-sensitive classifier, and serves real-time predictions
backed by **MLflow** model tracking.

> **Navigation tip:** If you landed here directly, read the root
> [`README.md`](../../README.md), [`src/README.md`](../README.md), and
> [`app/readme.md`](../../app/readme.md) to understand how this module
> fits into the broader MLOps streaming pipeline
> (Producer -> Cleaner -> Training -> Inference -> Quality Gates).

---

## Files

| File               | What it does                                                       |
|--------------------|--------------------------------------------------------------------|
| `__init__.py`      | Package marker; makes `src.ml` importable.                         |
| `features.py`      | Canonical feature list + feature-ordering/preprocessing helper.    |
| `prepare_data.py`  | Builds a balanced binary (BENIGN/ATTACK) dataset from JSONL logs.  |
| `balance_parquet.py` | Memory-friendly streaming under-sampling of the Parquet dataset.   |
| `train.py`         | Trains the XGBoost model, evaluates it, and logs to MLflow.        |
| `predict.py`       | Loads the model (MLflow or local fallback) and runs inference.      |

---

## 1. `features.py` — Feature Engineering

### `FEATURE_COLUMNS`
A `list[str]` of the **33 numeric features** (in order) expected by the
model. `destination_port`, `init_win_bytes_forward` and
`init_win_bytes_backward` were dropped (33 features instead of the
original 36) because they are constant or leakage-prone for this model.
Every `FlowItem` sent to the API provides exactly these fields.

### `preprocess_features(df: pd.DataFrame) -> pd.DataFrame`
Orders the DataFrame columns to match `FEATURE_COLUMNS` exactly (via
`reindex`) and replaces `+inf`/`-inf` values with `NaN` (XGBoost handles
missing values natively). No scaling is applied — the model is trained on
the raw, order-corrected flow features. Returns the cleaned DataFrame.

> This helper is imported by both `predict.py` (inference) and `train.py`
> (training) so the feature shape is identical at both stages.

---

## 2. `prepare_data.py` — Dataset Preparation

### `get_project_root() -> str`
Returns the repository root so file paths resolve regardless of the
current working directory.

### `prepare_binary_dataset(chunksize=100_000)`
1. Reads `data/exports/cleaned_logs.jsonl` in chunks.
2. Drops the multi-class `label` column and **downcasts** types to save
   memory (`float64->float32`, `int64->int32`).
3. **Undersamples** the majority class (`is_attack == 0 / BENIGN`) so the
   binary classes are balanced (1:1).
4. Writes the result to `data/exports/cleaned_logs_balanced.{csv,parquet}`.

Run manually:
```bash
python -m src.ml.prepare_data
```

---

## 3. `balance_parquet.py` — Streaming Undersampling

A standalone script (not imported by the API) that balances a large
`cleaned_logs.parquet` file by down-sampling the majority (BENIGN) class
to match the number of attack rows — done in chunks so it stays
memory-friendly on very large files.

```bash
python src/ml/balance_parquet.py
```

---

## 4. `train.py` — Model Training

### `get_project_root()` / `load_prepared_data(data_path=None) -> pd.DataFrame`
Locates the repo root and loads the balanced Parquet/CSV dataset (falls
back to the CSV if Parquet is missing).

### `train_model(data_path=None, n_estimators=150, max_depth=6, learning_rate=0.1, random_state=42) -> dict`
1. Loads the dataset and splits `X = FEATURE_COLUMNS` vs `y = is_attack`.
2. Computes **square-root dampened** sample weights from the granular
   `label` column so rare attack types are not drowned out:
   `weight = sqrt(total_samples / (num_classes * count_of_class))`.
3. Performs an **80/20 stratified** train/test split.
4. Trains an `XGBClassifier` with `sample_weight` on the training split.
5. Evaluates precision, recall, F1, and accuracy on the test split.
6. Saves artifacts to `src/ml/artifacts/`:
   - `model.joblib` — the trained model
   - `classification_report.txt`
   - `confusion_matrix.json`
7. If MLflow is installed, starts a run, logs params/metrics/tags, and
   registers the model as `network-anomaly-detector-xgboost`.

Run manually:
```bash
python -m src.ml.train
```

---

## 5. `predict.py` — Inference

### `get_project_root()`
Same helper as above.

### `load_model(model_path=None) -> Any`
Tries **MLflow first**
(`models:/network-anomaly-detector-xgboost/Production`), then falls back
to the local artifact at `src/ml/artifacts/model.joblib`. Returns `None`
if no model can be loaded.

### `predict(record: Dict, model=None) -> Tuple[int, float]`
Predicts whether a single record is an anomaly. Builds a single-row
DataFrame, preprocesses it, runs `model.predict`, and returns
`(label, confidence)` where `label` is `"ATTACK"` or `"BENIGN"` and
`confidence` comes from `predict_proba` when available (otherwise `1.0`).

### `predict_batch(records: List[Dict], model=None) -> List[Dict]`
Vectorized version: predicts a whole list at once and returns
`[{"is_anomaly": "ATTACK|...", "confidence": float}, ...]`.

---

## How It Fits Together

```
src/ml/predict.py   <-- loaded & called by app/main.py (/predict, /predict/batch)
src/ml/features.py  <-- canonical FEATURE_COLUMNS + preprocess_features (shared)
src/ml/train.py     <-- trains model.joblib -> artifacts/ -> MLflow registry
src/ml/prepare_data.py / balance_parquet.py <-- build the training dataset
```

The FastAPI service loads the model **once** at startup via
`load_model()` and keeps it in `app.state.model` for the lifetime of the
process.

> **See also:** [`app/readme.md`](../../app/readme.md) for the HTTP API,
> the Pydantic request schemas, and Prometheus/Grafana monitoring.
