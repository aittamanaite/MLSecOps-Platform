"""Feature engineering module for network anomaly detection.

Extracts and preprocesses features from CICIDS2017 network traffic logs.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple, Optional

# Top numeric features for anomaly detection
FEATURE_COLUMNS = [
    "destination_port",
    "flow_duration",
    "total_fwd_packets",
    "total_backward_packets",
    "total_length_of_fwd_packets",
    "total_length_of_bwd_packets",
    "fwd_packet_length_max",
    "fwd_packet_length_min",
    "fwd_packet_length_mean",
    "fwd_packet_length_std",
    "bwd_packet_length_max",
    "bwd_packet_length_min",
    "bwd_packet_length_mean",
    "bwd_packet_length_std",
    "flow_iat_mean",
    "flow_iat_std",
    "flow_iat_max",
    "flow_iat_min",
    "fwd_iat_total",
    "fwd_iat_mean",
    "fwd_iat_std",
    "bwd_iat_total",
    "bwd_iat_mean",
    "bwd_iat_std",
    "fin_flag_count",
    "syn_flag_count",
    "rst_flag_count",
    "psh_flag_count",
    "ack_flag_count",
    "average_packet_size",
    "init_win_bytes_forward",
    "init_win_bytes_backward",
    "active_mean",
    "active_std",
    "idle_mean",
    "idle_std",
]

def extract_features(records: List[Dict]) -> pd.DataFrame:
    """Extract feature columns from a list of cleaned records.

    Args:
        records: List of dictionaries representing network flows.

    Returns:
        DataFrame containing only the numeric features, with NaNs filled with 0.
    """
    df = pd.DataFrame(records)
    # Ensure all required columns exist
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
            
    df_features = df[FEATURE_COLUMNS].copy()
    # Fill NaN and infinite values
    df_features.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_features.fillna(0.0, inplace=True)
    
    return df_features

def extract_labels(records: List[Dict]) -> np.ndarray:
    """Extract is_attack labels.

    Args:
        records: List of dictionaries.

    Returns:
        Numpy array of labels (1 for attack, 0 for benign).
    """
    df = pd.DataFrame(records)
    if "is_attack" in df.columns:
        return df["is_attack"].fillna(0).astype(int).values
    return np.zeros(len(records), dtype=int)

def get_feature_scaler() -> StandardScaler:
    """Get a new StandardScaler instance.

    Returns:
        StandardScaler object.
    """
    return StandardScaler()

def preprocess_features(
    df: pd.DataFrame, 
    scaler: Optional[StandardScaler] = None, 
    fit: bool = False
) -> Tuple[np.ndarray, StandardScaler]:
    """Scale features using StandardScaler.

    Args:
        df: DataFrame with features.
        scaler: Pre-existing scaler instance (optional).
        fit: Whether to fit the scaler to the data.

    Returns:
        Tuple of (scaled_features array, fitted scaler).
    """
    if scaler is None:
        scaler = get_feature_scaler()
        
    if fit:
        scaled_features = scaler.fit_transform(df)
    else:
        scaled_features = scaler.transform(df)
        
    return scaled_features, scaler
