"""Feature engineering module for network anomaly detection.

Extracts and preprocesses non-leaky numerical features from CICIDS2017 logs.
"""

import logging
from typing import Dict, List, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Sanitized numeric features (Free from identifiers, IPs, timestamps, and target leakage)
FEATURE_NAMES = [
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
    "flow_bytes_s",
    "flow_packets_s",
    "flow_iat_mean",
    "flow_iat_std",
    "flow_iat_max",
    "flow_iat_min",
    "fwd_iat_total",
    "fwd_iat_mean",
    "fwd_iat_std",
    "fwd_iat_max",
    "fwd_iat_min",
    "bwd_iat_total",
    "bwd_iat_mean",
    "bwd_iat_std",
    "bwd_iat_max",
    "bwd_iat_min",
    "fwd_psh_flags",
    "fwd_header_length",
    "bwd_header_length",
    "fwd_packets_s",
    "bwd_packets_s",
    "min_packet_length",
    "max_packet_length",
    "packet_length_mean",
    "packet_length_std",
    "packet_length_variance",
    "fin_flag_count",
    "syn_flag_count",
    "rst_flag_count",
    "psh_flag_count",
    "ack_flag_count",
    "urg_flag_count",
    "ece_flag_count",
    "down_up_ratio",
    "average_packet_size",
    "avg_fwd_segment_size",
    "avg_bwd_segment_size",
    "subflow_fwd_packets",
    "subflow_fwd_bytes",
    "subflow_bwd_packets",
    "subflow_bwd_bytes",
    "init_win_bytes_forward",
    "init_win_bytes_backward",
    "act_data_pkt_fwd",
    "min_seg_size_forward",
    "active_mean",
    "active_std",
    "active_max",
    "active_min",
    "idle_mean",
    "idle_std",
    "idle_max",
    "idle_min",
]

# Explicit list of sensitive / leakage columns to strip if present in raw records
SENSITIVE_COLUMNS_TO_DROP = [
    "flow_id",
    "source_ip",
    "src_ip",
    "source_port",
    "src_port",
    "destination_ip",
    "dst_ip",
    "timestamp",
    "label",
    "is_attack",
]


def extract_features(records: Union[List[Dict], pd.DataFrame]) -> pd.DataFrame:
    """Extract and sanitize feature columns from input records.

    Strips any sensitive or leaky columns and ensures output alignment with FEATURE_NAMES.
    """
    if isinstance(records, pd.DataFrame):
        df = records.copy()
    else:
        df = pd.DataFrame(records)

    if df.empty:
        return pd.DataFrame(columns=FEATURE_NAMES)

    # Drop any potential leaky/sensitive columns before feature extraction
    df.drop(columns=[c for c in SENSITIVE_COLUMNS_TO_DROP if c in df.columns], inplace=True, errors="ignore")

    # Fill missing expected features with 0.0
    for col in FEATURE_NAMES:
        if col not in df.columns:
            df[col] = 0.0

    df_features = df[FEATURE_NAMES].copy()

    # Clean infinite values resulting from division by zero
    df_features.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_features.fillna(0.0, inplace=True)

    return df_features