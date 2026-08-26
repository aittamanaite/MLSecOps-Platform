"""Tests for the ingestion module."""

import os


def test_ingest_data_creates_directory(tmp_path, monkeypatch):
    """Verify ingest_data() creates the raw data directory."""
    # Change to tmp_path to avoid polluting the real workspace
    monkeypatch.chdir(tmp_path)

    from src.ingestion.ingest import ingest_data

    result = ingest_data()

    assert result is True
    assert os.path.exists(os.path.join("data", "raw"))