"""
Unit tests for the Data Quality Validation Module.

Tests all three validation stages (raw CSV, cleaned records, inference output)
with known-good data, known-bad data, and edge cases.
"""

import pytest
import pandas as pd
import numpy as np

from src.quality.data_quality import (
    validate_raw_csv,
    validate_cleaned_records,
    validate_inference_output,
    DataQualityError,
    QualityReport,
    RuleResult,
    EXPECTED_RAW_COLUMNS,
    VALID_LABELS,
    MAX_NULL_RATE,
    MAX_DUPLICATE_RATE,
    ANOMALY_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Fixtures: Good data factories
# ---------------------------------------------------------------------------

@pytest.fixture
def good_raw_df():
    """Create a minimal valid CICIDS2017-style DataFrame with 79 columns."""
    # Build a single valid row matching ALL 79 expected columns
    # Note: "Fwd Header Length" appears twice in the real CSV (column 35 and 56)
    data = {
        "Destination Port": [80],
        "Flow Duration": [1000],
        "Total Fwd Packets": [10],
        "Total Backward Packets": [5],
        "Total Length of Fwd Packets": [500],
        "Total Length of Bwd Packets": [250],
        "Fwd Packet Length Max": [100],
        "Fwd Packet Length Min": [10],
        "Fwd Packet Length Mean": [50.0],
        "Fwd Packet Length Std": [20.0],
        "Bwd Packet Length Max": [80],
        "Bwd Packet Length Min": [5],
        "Bwd Packet Length Mean": [40.0],
        "Bwd Packet Length Std": [15.0],
        "Flow Bytes/s": [5000.0],
        "Flow Packets/s": [100.0],
        "Flow IAT Mean": [200.0],
        "Flow IAT Std": [50.0],
        "Flow IAT Max": [500],
        "Flow IAT Min": [10],
        "Fwd IAT Total": [800],
        "Fwd IAT Mean": [160.0],
        "Fwd IAT Std": [40.0],
        "Fwd IAT Max": [300],
        "Fwd IAT Min": [20],
        "Bwd IAT Total": [600],
        "Bwd IAT Mean": [120.0],
        "Bwd IAT Std": [30.0],
        "Bwd IAT Max": [250],
        "Bwd IAT Min": [15],
        "Fwd PSH Flags": [0],
        "Bwd PSH Flags": [0],
        "Fwd URG Flags": [0],
        "Bwd URG Flags": [0],
        "Fwd Header Length": [40],
        "Bwd Header Length": [32],
        "Fwd Packets/s": [50.0],
        "Bwd Packets/s": [25.0],
        "Min Packet Length": [5],
        "Max Packet Length": [100],
        "Packet Length Mean": [45.0],
        "Packet Length Std": [18.0],
        "Packet Length Variance": [324.0],
        "FIN Flag Count": [0],
        "SYN Flag Count": [1],
        "RST Flag Count": [0],
        "PSH Flag Count": [0],
        "ACK Flag Count": [1],
        "URG Flag Count": [0],
        "CWE Flag Count": [0],
        "ECE Flag Count": [0],
        "Down/Up Ratio": [0.5],
        "Average Packet Size": [50.0],
        "Avg Fwd Segment Size": [50.0],
        "Avg Bwd Segment Size": [40.0],
        "Fwd Avg Bytes/Bulk": [0],
        "Fwd Avg Packets/Bulk": [0],
        "Fwd Avg Bulk Rate": [0],
        "Bwd Avg Bytes/Bulk": [0],
        "Bwd Avg Packets/Bulk": [0],
        "Bwd Avg Bulk Rate": [0],
        "Subflow Fwd Packets": [10],
        "Subflow Fwd Bytes": [500],
        "Subflow Bwd Packets": [5],
        "Subflow Bwd Bytes": [250],
        "Init_Win_bytes_forward": [65535],
        "Init_Win_bytes_backward": [65535],
        "act_data_pkt_fwd": [5],
        "min_seg_size_forward": [20],
        "Active Mean": [100.0],
        "Active Std": [10.0],
        "Active Max": [200],
        "Active Min": [50],
        "Idle Mean": [300.0],
        "Idle Std": [50.0],
        "Idle Max": [500],
        "Idle Min": [100],
        "Label": ["BENIGN"],
    }
    df = pd.DataFrame(data)
    # The real CSV has "Fwd Header Length" twice (columns 35 and 56).
    # pandas deduplicates column names, so we have 78 unique columns in the dict.
    # We need to add a duplicate column to match the expected 79-column count.
    # Insert duplicate "Fwd Header Length" after "Avg Bwd Segment Size"
    cols = list(df.columns)
    idx = cols.index("Avg Bwd Segment Size") + 1
    # Create new df with duplicate column
    fwd_header_dup = df["Fwd Header Length"].copy()
    df.insert(idx, "Fwd Header Length", fwd_header_dup, allow_duplicates=True)
    return df


@pytest.fixture
def good_cleaned_records():
    """Create a list of valid cleaned records."""
    return [
        {
            "destination_port": 80,
            "flow_duration": 1000,
            "total_fwd_packets": 10,
            "total_backward_packets": 5,
            "label": "BENIGN",
            "flow_bytes/s": 5000.0,
            "fwd_packet_length_max": 100,
            "fwd_packet_length_min": 10,
            "bwd_packet_length_max": 80,
            "init_win_bytes_forward": 65535,
        },
        {
            "destination_port": 443,
            "flow_duration": 2000,
            "total_fwd_packets": 20,
            "total_backward_packets": 10,
            "label": "DoS Hulk",
            "flow_bytes/s": 10000.0,
            "fwd_packet_length_max": 200,
            "fwd_packet_length_min": 20,
            "bwd_packet_length_max": 160,
            "init_win_bytes_forward": 32768,
        },
    ]


@pytest.fixture
def good_inference_records():
    """Create a list of valid inference output records (anomalies)."""
    return [
        {
            "destination_port": 80,
            "label": "DoS Hulk",
            "ml_confidence_score": 0.95,
            "ml_model_version": "v1.2.0-isolation-forest",
        },
        {
            "destination_port": 22,
            "label": "SSH-Patator",
            "ml_confidence_score": 0.88,
            "ml_model_version": "v1.2.0-isolation-forest",
        },
    ]


# ===========================================================================
# Stage 1: Raw CSV Validation Tests
# ===========================================================================

class TestValidateRawCSV:
    """Tests for validate_raw_csv()."""

    def test_valid_data_passes(self, good_raw_df):
        """A properly formed CICIDS2017 DataFrame should pass all checks."""
        report = validate_raw_csv(good_raw_df)
        assert report.passed is True
        assert report.failed_rules == 0

    def test_empty_dataframe_fails(self):
        """An empty DataFrame should fail the row count check."""
        df = pd.DataFrame(columns=EXPECTED_RAW_COLUMNS)
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "row_count_minimum" in failed_names

    def test_wrong_column_count_fails(self):
        """A DataFrame with wrong number of columns should fail."""
        df = pd.DataFrame({"col1": [1], "col2": [2], "Label": ["BENIGN"]})
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "column_count_match" in failed_names

    def test_missing_critical_column_fails(self, good_raw_df):
        """Dropping a critical column should fail the critical columns check."""
        df = good_raw_df.drop(columns=["Label"])
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "critical_columns_present" in failed_names

    def test_high_label_null_rate_fails(self, good_raw_df):
        """If > 5% of Label values are null, the check should fail."""
        # Create a DF with 100 rows, 10 of which have null labels (10% > 5%)
        df = pd.concat([good_raw_df] * 100, ignore_index=True)
        df.loc[0:9, "Label"] = None
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "label_null_rate" in failed_names

    def test_fully_empty_rows_fails(self, good_raw_df):
        """Rows with all-NaN values should be caught."""
        df = pd.concat([good_raw_df] * 2, ignore_index=True)
        # Set all values in row 1 to NaN
        df.iloc[1] = np.nan
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "no_fully_empty_rows" in failed_names

    def test_invalid_port_range_fails(self, good_raw_df):
        """Port values outside [0, 65535] should be caught."""
        df = good_raw_df.copy()
        df["Destination Port"] = [99999]
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "port_range_valid" in failed_names

    def test_invalid_label_fails(self, good_raw_df):
        """Unknown label values should be caught."""
        df = good_raw_df.copy()
        df["Label"] = ["UNKNOWN_ATTACK"]
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "label_values_valid" in failed_names

    def test_infinite_values_fails(self, good_raw_df):
        """Infinite values in numeric columns should be caught."""
        df = good_raw_df.copy()
        df["Flow Duration"] = [float("inf")]
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "no_infinite_values" in failed_names

    def test_negative_values_fails(self, good_raw_df):
        """Negative values in non-negative columns should be caught."""
        df = good_raw_df.copy()
        df["Flow Duration"] = [-100]
        with pytest.raises(DataQualityError) as exc_info:
            validate_raw_csv(df)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "non_negative_numerics" in failed_names

    def test_boundary_port_values_pass(self, good_raw_df):
        """Port values 0 and 65535 should both be valid."""
        df0 = good_raw_df.copy()
        df0["Destination Port"] = [0]
        report0 = validate_raw_csv(df0)
        assert report0.passed

        df_max = good_raw_df.copy()
        df_max["Destination Port"] = [65535]
        report_max = validate_raw_csv(df_max)
        assert report_max.passed


# ===========================================================================
# Stage 2: Cleaned Records Validation Tests
# ===========================================================================

class TestValidateCleanedRecords:
    """Tests for validate_cleaned_records()."""

    def test_valid_records_pass(self, good_cleaned_records):
        """Properly formed cleaned records should pass all checks."""
        report = validate_cleaned_records(good_cleaned_records)
        assert report.passed is True
        assert report.failed_rules == 0

    def test_empty_records_fails(self):
        """An empty list should fail the record count check."""
        with pytest.raises(DataQualityError) as exc_info:
            validate_cleaned_records([])
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "record_count_minimum" in failed_names

    def test_missing_critical_keys_fails(self):
        """Records missing critical keys should fail."""
        records = [{"some_random_key": 42}]
        with pytest.raises(DataQualityError) as exc_info:
            validate_cleaned_records(records)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "critical_keys_present" in failed_names

    def test_non_normalized_keys_fails(self):
        """Keys with uppercase or spaces should fail the normalization check."""
        records = [
            {
                "Destination Port": 80,  # Not snake_case!
                "flow_duration": 1000,
                "total_fwd_packets": 10,
                "label": "BENIGN",
                "destination_port": 80,
                "key1": 1, "key2": 2, "key3": 3,
                "key4": 4, "key5": 5, "key6": 6,
            }
        ]
        with pytest.raises(DataQualityError) as exc_info:
            validate_cleaned_records(records)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "keys_normalized" in failed_names

    def test_invalid_port_in_cleaned_fails(self):
        """Invalid port values should fail."""
        records = [
            {
                "destination_port": 99999,
                "flow_duration": 1000,
                "total_fwd_packets": 10,
                "label": "BENIGN",
                "key1": 1, "key2": 2, "key3": 3,
                "key4": 4, "key5": 5, "key6": 6,
            }
        ]
        with pytest.raises(DataQualityError) as exc_info:
            validate_cleaned_records(records)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "port_values_valid" in failed_names

    def test_corrupted_record_low_field_count_fails(self):
        """Records with very few fields should fail the integrity check."""
        records = [{"a": 1, "b": 2}]  # Only 2 fields
        with pytest.raises(DataQualityError) as exc_info:
            validate_cleaned_records(records)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "record_field_count" in failed_names


# ===========================================================================
# Stage 3: Inference Output Validation Tests
# ===========================================================================

class TestValidateInferenceOutput:
    """Tests for validate_inference_output()."""

    def test_valid_inference_passes(self, good_inference_records):
        """Valid anomaly records should pass all checks."""
        report = validate_inference_output(good_inference_records, total_processed=100)
        assert report.passed is True
        assert report.failed_rules == 0

    def test_zero_anomalies_passes(self):
        """Zero anomalies is a valid outcome."""
        report = validate_inference_output([], total_processed=100)
        assert report.passed is True

    def test_missing_ml_metadata_fails(self):
        """Records without ml_confidence_score or ml_model_version should fail."""
        records = [{"destination_port": 80, "label": "DoS Hulk"}]
        with pytest.raises(DataQualityError) as exc_info:
            validate_inference_output(records, total_processed=10)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "ml_metadata_present" in failed_names

    def test_confidence_out_of_range_fails(self):
        """Confidence scores outside [0.0, 1.0] should fail."""
        records = [
            {
                "ml_confidence_score": 1.5,
                "ml_model_version": "v1.0",
            }
        ]
        with pytest.raises(DataQualityError) as exc_info:
            validate_inference_output(records, total_processed=10)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "confidence_range_valid" in failed_names

    def test_confidence_negative_fails(self):
        """Negative confidence scores should fail."""
        records = [
            {
                "ml_confidence_score": -0.5,
                "ml_model_version": "v1.0",
            }
        ]
        with pytest.raises(DataQualityError) as exc_info:
            validate_inference_output(records, total_processed=10)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "confidence_range_valid" in failed_names

    def test_empty_model_version_fails(self):
        """Empty model version string should fail."""
        records = [
            {
                "ml_confidence_score": 0.95,
                "ml_model_version": "",
            }
        ]
        with pytest.raises(DataQualityError) as exc_info:
            validate_inference_output(records, total_processed=10)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "model_version_valid" in failed_names

    def test_below_threshold_fails(self):
        """Anomaly records with confidence <= threshold should fail."""
        records = [
            {
                "ml_confidence_score": 0.50,  # Below 0.80
                "ml_model_version": "v1.0",
            }
        ]
        with pytest.raises(DataQualityError) as exc_info:
            validate_inference_output(records, total_processed=10)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "threshold_consistency" in failed_names

    def test_anomaly_count_exceeds_total_fails(self):
        """More anomalies than total processed records is implausible."""
        records = [
            {
                "ml_confidence_score": 0.95,
                "ml_model_version": "v1.0",
            }
        ] * 20
        with pytest.raises(DataQualityError) as exc_info:
            validate_inference_output(records, total_processed=5)
        report = exc_info.value.report
        failed_names = [r.rule_name for r in report.results if not r.passed]
        assert "anomaly_count_plausible" in failed_names

    def test_boundary_confidence_1_passes(self):
        """Confidence score of exactly 1.0 should be valid."""
        records = [
            {
                "ml_confidence_score": 1.0,
                "ml_model_version": "v1.0",
            }
        ]
        report = validate_inference_output(records, total_processed=10)
        assert report.passed is True


# ===========================================================================
# Report and Error Tests
# ===========================================================================

class TestQualityReportAndError:
    """Tests for QualityReport and DataQualityError."""

    def test_report_summary_contains_stage(self):
        """Report summary should include the stage name."""
        report = QualityReport(stage="test_stage")
        report.add_result(RuleResult(
            rule_name="test_rule",
            category="completeness",
            passed=True,
            message="OK",
        ))
        summary = report.summary()
        assert "test_stage" in summary
        assert "PASSED" in summary

    def test_report_to_dict(self):
        """Report.to_dict() should produce a serializable dictionary."""
        report = QualityReport(stage="test")
        report.add_result(RuleResult(
            rule_name="r1", category="validity", passed=True, message="ok"
        ))
        d = report.to_dict()
        assert d["stage"] == "test"
        assert d["passed"] is True
        assert len(d["results"]) == 1

    def test_data_quality_error_carries_report(self):
        """DataQualityError should carry the failing report."""
        report = QualityReport(stage="fail_test")
        report.add_result(RuleResult(
            rule_name="bad", category="integrity", passed=False, message="fail"
        ))
        err = DataQualityError(report)
        assert err.report.passed is False
        assert "fail_test" in str(err)
