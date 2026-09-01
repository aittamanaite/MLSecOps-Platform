# Application API (`app/`)

A FastAPI service that loads a trained XGBoost model at startup and
exposes network-anomaly-detection endpoints plus a Prometheus metrics
endpoint.

> **Navigation tip:** Read this file together with the root
> [`README.md`](../README.md), [`src/README.md`](../src/README.md),
> and [`src/ml/readme.md`](../src/ml/readme.md) to understand the
> training/inference pipeline that produces the model this API serves.

---

## Files

| File           | What it does                                                |
|----------------|-------------------------------------------------------------|
| `__init__.py`  | Package marker; exposes the `app` package.                  |
| `main.py`      | FastAPI app: endpoints, startup model loading, metrics.     |
| `models.py`    | Pydantic request schemas (`FlowItem`, `BatchPredictRequest`).|
| `entrypoint.sh`| Container entrypoint that execs the uvicorn command.        |
| `.dockerfile`  | Container image build definition for the API.               |
| `tests/`       | Pytest suite + fixtures for the API.                        |

---

## Pydantic Schemas (`app/models.py`)

### `FlowItem`
A single network-flow record. **All 33 fields are required**; their
names map 1:1 to `FEATURE_COLUMNS` in `src/ml/features.py`.

| Field                              | Type  | | Field              | Type  |
|------------------------------------|-------|-|------------------------|-------|
| `flow_duration`                    | float | | `fwd_iat_total`        | float |
| `total_fwd_packets`                | int   | | `fwd_iat_mean`         | float |
| `total_backward_packets`           | int   | | `fwd_iat_std`          | float |
| `total_length_of_fwd_packets`      | float | | `bwd_iat_total`        | float |
| `total_length_of_bwd_packets`      | float | | `bwd_iat_mean`         | float |
| `fwd_packet_length_max`            | float | | `bwd_iat_std`          | float |
| `fwd_packet_length_min`            | float | | `fin_flag_count`       | int   |
| `fwd_packet_length_mean`           | float | | `syn_flag_count`       | int   |
| `fwd_packet_length_std`            | float | | `rst_flag_count`       | int   |
| `bwd_packet_length_max`            | float | | `psh_flag_count`       | int   |
| `bwd_packet_length_min`            | float | | `ack_flag_count`       | int   |
| `bwd_packet_length_mean`           | float | | `average_packet_size`  | float |
| `bwd_packet_length_std`            | float | | `active_mean`          | float |
| `flow_iat_mean`                    | float | | `active_std`           | float |
| `flow_iat_std`                     | float | | `idle_mean`            | float |
| `flow_iat_max`                     | float | | `idle_std`             | float |
| `flow_iat_min`                     | float | |                        |       |

### `BatchPredictRequest`
A wrapped batch payload accepted by `POST /predict/batch`.

```jsonc
{ "flows": [ <FlowItem>, <FlowItem>, ... ] }
```

---

## Endpoints

Open the auto-generated docs once the service is running:
- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

### `GET /health` — Readiness probe

**Response** `200 OK`

| Field           | Type   | Description                                  |
|-----------------|--------|----------------------------------------------|
| `status`        | string | `"ok"` when the model is loaded, else `"degraded"` |
| `model_loaded`  | bool   | `true` if the model was loaded at startup     |

```bash
curl -s http://localhost:8000/health
```

---

### `POST /predict` — Single-flow prediction

**Body:** a `FlowItem` JSON object (all 33 fields required).

**Response** `200 OK`

| Field        | Type    | Description                          |
|--------------|---------|--------------------------------------|
| `is_anomaly` | string  | `"ATTACK"` or `"BENIGN"`             |
| `confidence` | float   | Probability of the predicted class (`0.0-1.0`) |

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @samples/flow_record.json
```

**Error responses**

| Status | When                                             |
|--------|--------------------------------------------------|
| 503    | Model is not loaded / service still initializing  |
| 422    | Body fails Pydantic validation (missing/invalid fields) |
| 500    | Internal model error during inference            |

---

### `POST /predict/batch` — Bulk prediction

**Body:** either a bare JSON array of `FlowItem` objects (recommended) or
a `BatchPredictRequest` object (`{"flows": [FlowItem, ...]}`).

**Response** `200 OK`

| Field            | Type   | Description                              |
|------------------|--------|------------------------------------------|
| `predictions`    | array  | `is_anomaly` + `confidence` per record   |
| `total_processed` | int   | Number of records processed              |
| `anomalies_found` | int   | Number of records flagged as `ATTACK`    |

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '[ { <FlowItem> }, { <FlowItem> } ]'
```

**Error responses**

| Status | When                                       |
|--------|--------------------------------------------|
| 422    | Empty list, or any record fails validation |
| 503    | Model is not loaded                        |
| 500    | Internal model error                       |

---

### `GET /metrics` — Prometheus metrics

Returns in-app metrics in the Prometheus text exposition format.

```bash
curl -s http://localhost:8000/metrics
```

| Metric                    | Type     | Meaning                                            |
|---------------------------|----------|----------------------------------------------------|
| `model_predictions_total` | Counter  | Total predictions (label: `model_version`)         |
| `anomalies_detected_total`| Counter  | Total flows flagged as anomalies                   |
| `model_inference_seconds` | Histogram| Per-request inference duration (seconds)           |

---

## How to Run

### Locally

```bash
export PYTHONPATH=.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The model is loaded at startup from `src/ml/artifacts/model.joblib`
(MLflow is tried first). If absent, `/health` reports `degraded` and
`/predict` returns `503`.

### Docker Compose

```bash
docker compose up --build -d fastapi-app   # the API only
docker compose up --build                  # the whole stack
```

The API is exposed on **`http://localhost:8000`**.

### Tests

```bash
python -m pytest app/tests -v
```

The suite uses a mocked model injected into `app.state`, so you can test
`/health`, `/predict`, `/predict/batch`, `/metrics`, and validation
failures without a real model artifact.

---

## How to Open & Use Prometheus and Grafana

Both services are defined in [`docker-compose.yml`](../docker-compose.yml)
and Prometheus is configured in [`prometheus.yml`](../prometheus.yml) to
scrape `fastapi-app:8000/metrics` every 15s.

### 1. Start the stack

```bash
docker compose up -d fastapi-app prometheus grafana
```

Host port mapping (see `docker-compose.yml`):

| Service   | Host port | URL                      |
|-----------|-----------|--------------------------|
| FastAPI   | 8000      | http://localhost:8000    |
| Prometheus| 9090      | http://localhost:9090    |
| Grafana   | 3001      | http://localhost:3001    |

> Grafana runs on `3000` inside the container but is mapped to host port
> `3001` to avoid clashing with Dagster (on `3000`).

### 2. Open Prometheus

- Go to **http://localhost:9090** (no login required).
- In the **Expression** bar paste a query and click **Execute**, then
  switch to the **Graph** tab:
  ```promql
  # Total predictions per second
  rate(model_predictions_total[5m])

  # Anomaly rate (anomalies / predictions)
  rate(anomalies_detected_total[5m]) / rate(model_predictions_total[5m])

  # Average inference latency (seconds)
  rate(model_inference_seconds_sum[5m]) / rate(model_inference_seconds_count[5m])

  # 95th-percentile inference latency
  histogram_quantile(0.95, rate(model_inference_seconds_bucket[5m]))
  ```
- Prometheus reads its scrape config from `prometheus.yml`, which points
  at the FastAPI `/metrics` endpoint.

### 3. Open Grafana

- Go to **http://localhost:3001**. Default login: `admin` / `admin`
  (password set in compose via `GF_SECURITY_ADMIN_PASSWORD`).

#### Add Prometheus as a data source

1. **Connections -> Data sources -> Create data source**.
2. Select **Prometheus**.
3. Set **URL** to `http://prometheus:9090`
   (use the Docker service name `prometheus` since Grafana runs on the
   same compose network).
4. Click **Save & Test** — should show *Data source is working*.

#### Build a dashboard

1. **Create -> Dashboard -> Add new panel**.
2. Select the Prometheus data source.
3. Copy the PromQL queries from the table above into panels. A useful
   layout:

| Panel                 | Query                                                       |
|-----------------------|-------------------------------------------------------------|
| Total predictions     | `rate(model_predictions_total[5m])`                         |
| Anomalies detected    | `rate(anomalies_detected_total[5m])`                        |
| Anomaly rate          | `rate(anomalies_detected_total[5m]) / rate(model_predictions_total[5m])` |
| Avg inference latency | `rate(model_inference_seconds_sum[5m]) / rate(model_inference_seconds_count[5m])` |
| p95 inference latency | `histogram_quantile(0.95, rate(model_inference_seconds_bucket[5m]))` |

4. **Save** the dashboard (e.g. *Anomaly Detection Metrics*).

---

> **See also:** [`src/ml/readme.md`](../src/ml/readme.md) for model
> loading, training, and feature details.
