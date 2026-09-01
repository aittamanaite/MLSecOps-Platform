"""Parquet dataset balancing module.

Performs memory-friendly, streaming under-sampling on large Parquet datasets 
to balance majority (BENIGN) and minority (ATTACK) classes efficiently.
"""

import logging
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Returns absolute path to project root."""
    return Path(__file__).resolve().parent.parent.parent


def balance_parquet_dataset(
    input_parquet: Union[str, Path],
    output_parquet: Union[str, Path],
    target_column: str = "is_attack",
    random_state: int = 42,
) -> None:
    """Under-samples the majority class in a Parquet dataset to produce a 1:1 balanced output.

    Reads metadata/schema dynamically to avoid OOM errors on large traffic datasets.

    Args:
        input_parquet: Path to source imbalanced Parquet file.
        output_parquet: Destination path for balanced Parquet dataset.
        target_column: Name of binary target column (1=ATTACK, 0=BENIGN).
        random_state: Seed for reproducible sampling.
    """
    input_path = Path(input_parquet)
    output_path = Path(output_parquet)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        logger.error(f"Input file not found at {input_path}")
        raise FileNotFoundError(f"Input Parquet file not found at {input_path}")

    logger.info(f"Scanning Parquet metadata from {input_path}...")
    parquet_file = pq.ParquetFile(input_path)

    # 1. First pass: Pass over column data to count class frequencies efficiently
    logger.info("Calculating class distributions...")
    df_labels = parquet_file.read(columns=[target_column]).to_pandas()
    
    attack_indices = df_labels[df_labels[target_column] == 1].index.to_numpy()
    benign_indices = df_labels[df_labels[target_column] == 0].index.to_numpy()

    num_attacks = len(attack_indices)
    num_benign = len(benign_indices)

    logger.info(f"Raw Counts -> ATTACK (minority): {num_attacks}, BENIGN (majority): {num_benign}")

    if num_attacks == 0:
        logger.error("No ATTACK samples found in dataset. Cannot balance.")
        return

    if num_benign <= num_attacks:
        logger.info("Dataset is already balanced or majority class is smaller. Copying as is.")
        df_full = parquet_file.read().to_pandas()
        df_full.to_parquet(output_path, index=False)
        return

    # 2. Random under-sampling of majority class
    np.random.seed(random_state)
    sampled_benign_indices = np.random.choice(benign_indices, size=num_attacks, replace=False)

    # Combine indices and sort for sequential memory access
    balanced_indices = np.sort(np.concatenate([attack_indices, sampled_benign_indices]))

    logger.info(f"Under-sampled majority class to {num_attacks} records. Total balanced rows: {len(balanced_indices)}")

    # 3. Read dataset in chunks and filter according to sampled indices
    logger.info("Filtering and writing balanced dataset...")
    df_full = parquet_file.read().to_pandas()
    df_balanced = df_full.iloc[balanced_indices].reset_index(drop=True)

    # Save final balanced dataset
    df_balanced.to_parquet(output_path, index=False)

    logger.info(f"Successfully saved balanced dataset to {output_path}")
    logger.info(f"Final Distribution -> BENIGN: {num_attacks}, ATTACK: {num_attacks}")


if __name__ == "__main__":
    root = get_project_root()
    prepared_file = root / "data" / "exports" / "cleaned_logs.parquet"
    balanced_file = root / "data" / "exports" / "cleaned_logs_balanced.parquet"

    if prepared_file.exists():
        balance_parquet_dataset(prepared_file, balanced_file)
    else:
        logger.info(f"Input file {prepared_file} does not exist. Run prepare_data.py first.")