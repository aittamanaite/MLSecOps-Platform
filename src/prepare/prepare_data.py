"""Data preparation module for network anomaly detection.

Reads raw JSONL streaming log records, applies sanitization/feature extraction
without data leakage, and outputs a clean binary (BENIGN/ATTACK) Parquet dataset.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from src.ml.features import extract_features, extract_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Returns absolute path to project root."""
    return Path(__file__).resolve().parent.parent.parent


def process_jsonl_logs(
    input_file: Union[str, Path],
    output_parquet: Union[str, Path],
    chunksize: int = 50_000,
) -> None:
    """Processes streaming JSONL network logs and writes clean feature data to Parquet.

    Args:
        input_file: Path to source raw .jsonl file.
        output_parquet: Destination path for output .parquet file.
        chunksize: Number of lines to process per iteration to manage RAM.
    """
    input_path = Path(input_file)
    output_path = Path(output_parquet)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        raise FileNotFoundError(f"Input JSONL file not found at {input_path}")

    logger.info(f"Processing JSONL logs from {input_path} in chunks of {chunksize}...")

    processed_chunks = []
    chunk = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            chunk.append(json.loads(line))

            if len(chunk) >= chunksize:
                df_chunk = _transform_chunk(chunk)
                processed_chunks.append(df_chunk)
                chunk = []

        # Process remaining lines
        if chunk:
            df_chunk = _transform_chunk(chunk)
            processed_chunks.append(df_chunk)

    if not processed_chunks:
        logger.warning("No valid records were parsed from the input file.")
        return

    # Combine all processed chunks and save to Parquet
    full_df = pd.concat(processed_chunks, ignore_index=True)
    full_df.to_parquet(output_path, index=False)

    total_records = len(full_df)
    attack_count = int(full_df["is_attack"].sum())
    benign_count = total_records - attack_count

    logger.info(f"Successfully wrote {total_records} records to {output_path}")
    logger.info(f"Dataset Distribution -> BENIGN: {benign_count}, ATTACK: {attack_count}")


def _transform_chunk(raw_records: List[dict]) -> pd.DataFrame:
    """Helper to transform a raw batch of dicts into feature matrix + labels."""
    df_features = extract_features(raw_records)
    labels = extract_labels(raw_records)
    df_features["is_attack"] = labels
    return df_features


if __name__ == "__main__":
    root = get_project_root()
    raw_jsonl = root / "data" / "exports" / "cleaned_logs.jsonl"
    prepared_parquet = root / "data" / "exports" / "cleaned_logs.parquet"

    if raw_jsonl.exists():
        process_jsonl_logs(raw_jsonl, prepared_parquet)
    else:
        logger.info(f"Place raw JSONL logs in {raw_jsonl} and run this script.")