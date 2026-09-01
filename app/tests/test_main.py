"""Integration tests for the FastAPI Anomaly Detection API.

Tests health checks, single predictions, batch predictions, and Prometheus metrics
using TestClient and mocked ML model inference.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.app import app


@pytest.fixture
def dummy_flow_item():
    """Provides a valid dictionary representing a single network flow (33 features)."""
    return {
        "flow_duration": 12000.0,
        "total_fwd_packets": 10,
        "total_backward_packets": 8,
        "total_length_of_fwd_packets": 1024.0,
        "total_length_of_bwd_packets": 2048.0,
        "fwd_packet_length_max": 512.0,
        "fwd_packet_length_min": 64.0,
        "fwd_packet_length_mean": 256.0,
        "fwd_packet_length_std": 12.5,
        "bwd_packet_length_max": 1024.0,
        "bwd_packet_length_min": 64.0,
        "bwd_packet_length_mean": 512.0,
        "bwd_packet_length_std": 20.0,
        "flow_bytes_s": 256000.0,
        "flow_packets_s": 1500.0,
        "flow_iat_mean": 100.0,
        "flow_iat_std": 10.0,
        "flow_iat_max": 200.0,
        "flow_iat_min": 5.0,
        "fwd_iat_total": 1000.0,
        "fwd_iat_mean": 100.0,
        "fwd_iat_std": 10.0,
        "fwd_iat_max": 200.0,
        "fwd_iat_min": 5.0,
        "bwd_iat_total": 800.0,
        "bwd_iat_mean": 100.0,
        "bwd_iat_std": 10.0,
        "bwd_iat_max": 200.0,
        "bwd_iat_min": 5.0,
        "fwd_header_length": 200,
        "bwd_header_length": 160,
        "fwd_packets_s": 833.3,
        "bwd_packets_s": 666.7,
    }


@pytest.fixture
def mock_model():
    """Returns a mocked model object."""
    return MagicMock()


@pytest.fixture
def client(mock_model):
    """Creates a TestClient with a pre-loaded mock model attached to app.state."""
    with patch("app.app.load_model", return_value=mock_model):
        with TestClient(app) as test_client:
            yield test_client


# 1. Health Probe Tests
# -------------------------------------------------------------
def test_health_check_ok(client):
    """Test /health endpoint when model is loaded."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True


def test_health_check_degraded():
    """Test /health endpoint when model fails to load."""
    with patch("app.app.load_model", return_value=None):
        with TestClient(app) as client_unloaded:
            response = client_unloaded.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["model_loaded"] is False


# 2. Single Prediction Endpoint (/predict) Tests
# -------------------------------------------------------------
@patch("app.app.predict")
def test_predict_single_flow_success(mock_predict_func, client, dummy_flow_item):
    """Test successful single prediction call."""
    mock_predict_func.return_value = ("ATTACK", 0.98)

    response = client.post("/predict", json=dummy_flow_item)

    assert response.status_code == 200
    data = response.json()
    assert data["is_anomaly"] == "ATTACK"
    assert data["confidence"] == 0.98
    mock_predict_func.assert_called_once()


def test_predict_invalid_schema(client):
    """Test validation error when missing required flow fields."""
    incomplete_payload = {"flow_duration": 100.0}  # Missing required features
    response = client.post("/predict", json=incomplete_payload)

    assert response.status_code == 422  # Unprocessable Entity


def test_predict_service_unavailable():
    """Test 503 error when endpoint is called without a loaded model."""
    with patch("app.app.load_model", return_value=None):
        with TestClient(app) as client_no_model:
            response = client_no_model.post("/predict", json={})
            assert response.status_code == 503


# 3. Batch Prediction Endpoint (/predict/batch) Tests
# -------------------------------------------------------------
@patch("app.app.predict_batch")
def test_predict_batch_as_list(mock_batch_func, client, dummy_flow_item):
    """Test batch prediction using direct JSON list payload."""
    mock_batch_func.return_value = [
        {"is_anomaly": "BENIGN", "confidence": 0.99},
        {"is_anomaly": "ATTACK", "confidence": 0.95},
    ]

    payload = [dummy_flow_item, dummy_flow_item]
    response = client.post("/predict/batch", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert data["anomalies_found"] == 1
    assert len(data["predictions"]) == 2


@patch("app.app.predict_batch")
def test_predict_batch_as_wrapper_object(mock_batch_func, client, dummy_flow_item):
    """Test batch prediction using BatchPredictRequest wrapper object."""
    mock_batch_func.return_value = [
        {"is_anomaly": "ATTACK", "confidence": 0.91},
    ]

    payload = {"flows": [dummy_flow_item]}
    response = client.post("/predict/batch", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 1
    assert data["anomalies_found"] == 1


def test_predict_batch_empty_list(client):
    """Test validation error when sending an empty batch list."""
    response = client.post("/predict/batch", json=[])
    assert response.status_code == 422


# 4. Prometheus Metrics Endpoint Tests
# -------------------------------------------------------------
def test_prometheus_metrics_endpoint(client):
    """Test /metrics scrape endpoint return type and contents."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "model_predictions_total" in response.text