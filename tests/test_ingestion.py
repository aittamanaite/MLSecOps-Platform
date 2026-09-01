import os
from src.ingestion.ingest import ingest_data

def test_ingest_data_creates_directory():
    # Run ingestion process
    result = ingest_data()
    
    # Assert return status and folder existence
    assert result is True
    assert os.path.exists(os.path.join("data", "raw"))