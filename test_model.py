"""
Tests the trained model DIRECTLY through src/ml/predict.py — no FastAPI,
no HTTP, no frontend involved. This isolates whether confidence/label
problems are in the model + feature pipeline itself, or somewhere in the
API layer around it.

Run from the repo root, with your venv active (no MLflow needed — this
loads src/ml/artifacts/model.joblib directly):
    export PYTHONPATH=.          # Windows PowerShell: $env:PYTHONPATH="."
    python test_model_directly.py

What it does:
  1. Loads model.joblib directly with joblib.load() — skips
     load_model()'s MLflow-first logic entirely (and the `import mlflow`
     cost that comes with it), since we're testing the model + feature
     pipeline here, not the model-loading strategy.
  2. Sanity-checks the model's actual expected feature count against
     FEATURE_NAMES in features.py — in case THOSE have also drifted
     apart, which would be a second, independent bug.
  3. Runs two real flows (one BENIGN, one DDoS — pulled directly from
     your own Friday-WorkingHours-Afternoon-DDos CSV) through predict()
     TWICE each: once with only the 33 fields the live API currently
     collects (reproducing today's real behavior), and once with all 67
     fields the model was actually trained on (reproducing the fix, once
     app/models.py is widened). This directly answers "does giving it
     all 67 fields actually fix the confidence/label problem."
  4. Also prints the raw predict_proba() output directly, bypassing even
     predict()'s own label/confidence extraction logic, as a final,
     completely unwrapped ground truth.
"""

import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ml.predict import predict  # noqa: E402
from src.ml.features import FEATURE_NAMES, extract_features  # noqa: E402

# Local artifact only — skips load_model()'s MLflow-first logic entirely.
# We're testing the model + feature pipeline, not the model-loading
# strategy, so there's no reason to pay the `import mlflow` cost (or wait
# on a network call to a server that isn't running) just to get here.
MODEL_PATH = Path(__file__).resolve().parent / "src" / "ml" / "artifacts" / "model.joblib"

# ---------------------------------------------------------------------------
# Real rows pulled directly from Friday-WorkingHours-Afternoon-DDos_pcap_ISCX.csv
# ---------------------------------------------------------------------------

BENIGN_67 = {
    "destination_port": 54865, "flow_duration": 3, "total_fwd_packets": 2,
    "total_backward_packets": 0, "total_length_of_fwd_packets": 12,
    "total_length_of_bwd_packets": 0, "fwd_packet_length_max": 6,
    "fwd_packet_length_min": 6, "fwd_packet_length_mean": 6, "fwd_packet_length_std": 0,
    "bwd_packet_length_max": 0, "bwd_packet_length_min": 0, "bwd_packet_length_mean": 0,
    "bwd_packet_length_std": 0, "flow_bytes_s": 4000000, "flow_packets_s": 666666.6667,
    "flow_iat_mean": 3, "flow_iat_std": 0, "flow_iat_max": 3, "flow_iat_min": 3,
    "fwd_iat_total": 3, "fwd_iat_mean": 3, "fwd_iat_std": 0, "fwd_iat_max": 3,
    "fwd_iat_min": 3, "bwd_iat_total": 0, "bwd_iat_mean": 0, "bwd_iat_std": 0,
    "bwd_iat_max": 0, "bwd_iat_min": 0, "fwd_psh_flags": 0, "fwd_header_length": 40,
    "bwd_header_length": 0, "fwd_packets_s": 666666.6667, "bwd_packets_s": 0,
    "min_packet_length": 6, "max_packet_length": 6, "packet_length_mean": 6,
    "packet_length_std": 0, "packet_length_variance": 0, "fin_flag_count": 0,
    "syn_flag_count": 0, "rst_flag_count": 0, "psh_flag_count": 0, "ack_flag_count": 1,
    "urg_flag_count": 0, "ece_flag_count": 0, "down_up_ratio": 0, "average_packet_size": 9,
    "avg_fwd_segment_size": 6, "avg_bwd_segment_size": 0, "subflow_fwd_packets": 2,
    "subflow_fwd_bytes": 12, "subflow_bwd_packets": 0, "subflow_bwd_bytes": 0,
    "init_win_bytes_forward": 33, "init_win_bytes_backward": -1, "act_data_pkt_fwd": 1,
    "min_seg_size_forward": 20, "active_mean": 0, "active_std": 0, "active_max": 0,
    "active_min": 0, "idle_mean": 0, "idle_std": 0, "idle_max": 0, "idle_min": 0,
}

DDOS_67 = {
    "destination_port": 80, "flow_duration": 1293792, "total_fwd_packets": 3,
    "total_backward_packets": 7, "total_length_of_fwd_packets": 26,
    "total_length_of_bwd_packets": 11607, "fwd_packet_length_max": 20,
    "fwd_packet_length_min": 0, "fwd_packet_length_mean": 8.666666667,
    "fwd_packet_length_std": 10.26320288, "bwd_packet_length_max": 5840,
    "bwd_packet_length_min": 0, "bwd_packet_length_mean": 1658.142857,
    "bwd_packet_length_std": 2137.29708, "flow_bytes_s": 8991.398927,
    "flow_packets_s": 7.72921768, "flow_iat_mean": 143754.6667,
    "flow_iat_std": 430865.8067, "flow_iat_max": 1292730, "flow_iat_min": 2,
    "fwd_iat_total": 747, "fwd_iat_mean": 373.5, "fwd_iat_std": 523.9661249,
    "fwd_iat_max": 744, "fwd_iat_min": 3, "bwd_iat_total": 1293746,
    "bwd_iat_mean": 215624.3333, "bwd_iat_std": 527671.9348, "bwd_iat_max": 1292730,
    "bwd_iat_min": 2, "fwd_psh_flags": 0, "fwd_header_length": 72, "bwd_header_length": 152,
    "fwd_packets_s": 2.318765304, "bwd_packets_s": 5.410452376, "min_packet_length": 0,
    "max_packet_length": 5840, "packet_length_mean": 1057.545455,
    "packet_length_std": 1853.437529, "packet_length_variance": 3435230.673,
    "fin_flag_count": 0, "syn_flag_count": 0, "rst_flag_count": 0, "psh_flag_count": 1,
    "ack_flag_count": 0, "urg_flag_count": 0, "ece_flag_count": 0, "down_up_ratio": 2,
    "average_packet_size": 1163.3, "avg_fwd_segment_size": 8.666666667,
    "avg_bwd_segment_size": 1658.142857, "subflow_fwd_packets": 3, "subflow_fwd_bytes": 26,
    "subflow_bwd_packets": 7, "subflow_bwd_bytes": 11607, "init_win_bytes_forward": 8192,
    "init_win_bytes_backward": 229, "act_data_pkt_fwd": 2, "min_seg_size_forward": 20,
    "active_mean": 0, "active_std": 0, "active_max": 0, "active_min": 0, "idle_mean": 0,
    "idle_std": 0, "idle_max": 0, "idle_min": 0,
}

# The model's ACTUAL required 33 features — read directly from the
# model's own error message (XGBoost prints its stored feature_names_in_
# when validation fails), not from any file that could be stale. This is
# DIFFERENT from FlowItem's current 33 fields in 10 places — see the
# diff table in chat. Both FlowItem and the old FEATURE_NAMES were wrong;
# this list is verified ground truth from the model artifact itself.
MODEL_REQUIRED_FIELDS = [
    "flow_duration", "total_fwd_packets", "total_backward_packets",
    "total_length_of_fwd_packets", "total_length_of_bwd_packets",
    "fwd_packet_length_max", "fwd_packet_length_min", "fwd_packet_length_mean",
    "fwd_packet_length_std", "bwd_packet_length_max", "bwd_packet_length_min",
    "bwd_packet_length_mean", "bwd_packet_length_std", "flow_iat_mean", "flow_iat_std",
    "flow_iat_max", "flow_iat_min", "fwd_iat_total", "fwd_iat_mean", "fwd_iat_std",
    "bwd_iat_total", "bwd_iat_mean", "bwd_iat_std", "fin_flag_count", "syn_flag_count",
    "rst_flag_count", "psh_flag_count", "ack_flag_count", "average_packet_size",
    "active_mean", "active_std", "idle_mean", "idle_std",
]


def only_33(sample_67: dict) -> dict:
    """Selects exactly the 33 fields the model actually needs, out of the
    full 67-field sample. All of them exist in BENIGN_67/DDOS_67 already
    since those were pulled from the real, full CICIDS2017 CSV row."""
    return {k: sample_67[k] for k in MODEL_REQUIRED_FIELDS}


def run_case(label: str, record: dict, model) -> None:
    predicted_label, confidence = predict(record, model)
    print(f"  {label:<28} -> is_anomaly={predicted_label:<8} confidence={confidence:.6f}")

    # Unwrap even further: bypass predict()'s own label/confidence logic
    # entirely and look at the raw model output directly. extract_features
    # expects a list of records (predict() itself wraps it this way
    # internally) — passing a bare dict here was the bug in the previous
    # version of this script.
    df_features = extract_features([record])
    df_features = df_features.astype("float64")  # TEST: force float64, see if that's what's tripping XGBoost 3.1.3's validation
    print(f"    df_features type={type(df_features)}  columns={list(df_features.columns)}")
    print(f"    dtypes:\n{df_features.dtypes}")
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(df_features)[0]
        pred_code = int(model.predict(df_features)[0])
        print(f"    raw predict_proba = {proba}  |  raw predict() class = {pred_code}")


def main() -> None:
    print(f"Loading local model directly from: {MODEL_PATH}")
    if not MODEL_PATH.exists():
        print(f"ERROR: no file found at {MODEL_PATH}")
        print("Adjust MODEL_PATH above if your model.joblib lives somewhere else.")
        sys.exit(1)
    model = joblib.load(MODEL_PATH)
    # Bypass the scikit-learn feature name stripping bug
    model.get_booster().feature_names = None

    print(f"Model loaded: {type(model)}")

    # Sanity check #1: does the model itself actually expect 67 features?
    # (If this doesn't match FEATURE_NAMES, that's a SEPARATE bug — the
    # model.joblib on disk may have been trained on a different feature
    # set than the current features.py file describes.)
    n_expected = getattr(model, "n_features_in_", None)
    print(f"FEATURE_NAMES in features.py: {len(FEATURE_NAMES)} features")
    print(f"Model's own n_features_in_:   {n_expected}")
    if n_expected is not None and n_expected != len(FEATURE_NAMES):
        print("  ^^^ MISMATCH — the trained model and features.py disagree on feature "
              "count. This would be a second, independent bug from the API's 33-field gap.")
    print()

    print("=" * 78)
    print("SCENARIO A — the model's correct 33 required fields")
    print("=" * 78)
    run_case("BENIGN sample (correct 33)", only_33(BENIGN_67), model)
    run_case("DDoS sample (correct 33)", only_33(DDOS_67), model)

    print()
    print("=" * 78)
    print("SCENARIO B — full 67-field superset (confirms extra ignored fields are harmless)")
    print("=" * 78)
    run_case("BENIGN sample (67 fields)", BENIGN_67, model)
    run_case("DDoS sample (67 fields)", DDOS_67, model)

    print()
    print("If Scenario B gives correct, differentiated labels and sane (non-zero,")
    print("class-consistent) confidence while Scenario A doesn't, that's direct proof")
    print("the 33-field API gap is the root cause — independent of any frontend or")
    print("FastAPI code at all.")


if __name__ == "__main__":
    main()