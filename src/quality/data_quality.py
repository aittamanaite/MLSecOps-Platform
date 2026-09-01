"""
Data Quality Validation Module for MLSecOps-Platform.

Defines quality rules (completeness, validity, integrity) for three pipeline stages:
  1. Raw CSV ingestion
  2. Cleaned streaming records
  3. ML inference output

Each stage validates data and raises DataQualityError on failure to halt the pipeline.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The 79 expected columns in the CICIDS2017 dataset (stripped of leading spaces)
EXPECTED_RAW_COLUMNS = [
    "Destination Port", "Flow Duration", "Total Fwd Packets",
    "Total Backward Packets", "Total Length of Fwd Packets",
    "Total Length of Bwd Packets", "Fwd Packet Length Max",
    "Fwd Packet Length Min", "Fwd Packet Length Mean",
    "Fwd Packet Length Std", "Bwd Packet Length Max",
    "Bwd Packet Length Min", "Bwd Packet Length Mean",
    "Bwd Packet Length Std", "Flow Bytes/s", "Flow Packets/s",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max",
    "Fwd IAT Min", "Bwd IAT Total", "Bwd IAT Mean", "Bwd IAT Std",
    "Bwd IAT Max", "Bwd IAT Min", "Fwd PSH Flags", "Bwd PSH Flags",
    "Fwd URG Flags", "Bwd URG Flags", "Fwd Header Length",
    "Bwd Header Length", "Fwd Packets/s", "Bwd Packets/s",
    "Min Packet Length", "Max Packet Length", "Packet Length Mean",
    "Packet Length Std", "Packet Length Variance", "FIN Flag Count",
    "SYN Flag Count", "RST Flag Count", "PSH Flag Count",
    "ACK Flag Count", "URG Flag Count", "CWE Flag Count",
    "ECE Flag Count", "Down/Up Ratio", "Average Packet Size",
    "Avg Fwd Segment Size", "Avg Bwd Segment Size",
    "Fwd Header Length", "Fwd Avg Bytes/Bulk",
    "Fwd Avg Packets/Bulk", "Fwd Avg Bulk Rate",
    "Bwd Avg Bytes/Bulk", "Bwd Avg Packets/Bulk",
    "Bwd Avg Bulk Rate", "Subflow Fwd Packets", "Subflow Fwd Bytes",
    "Subflow Bwd Packets", "Subflow Bwd Bytes",
    "Init_Win_bytes_forward", "Init_Win_bytes_backward",
    "act_data_pkt_fwd", "min_seg_size_forward", "Active Mean",
    "Active Std", "Active Max", "Active Min", "Idle Mean",
    "Idle Std", "Idle Max", "Idle Min", "Label",
]

# Critical columns that must be present (using stripped names)
CRITICAL_RAW_COLUMNS = [
    "Destination Port",
    "Flow Duration",
    "Protocol" if False else "Label",  # noqa – Label is the critical target column
]
# More precisely, these are the columns essential for the pipeline to function:
CRITICAL_COLUMNS_FOR_PIPELINE = [
    "Destination Port",
    "Label",
]

# Valid CICIDS2017 traffic labels
VALID_LABELS = {
    "BENIGN",
    "DoS Hulk",
    "PortScan",
    "DDoS",
    "DoS GoldenEye",
    "FTP-Patator",
    "SSH-Patator",
    "DoS slowloris",
    "DoS Slowhttptest",
    "Bot",
    "Web Attack \u2013 Brute Force",
    "Web Attack \u2013 XSS",
    "Web Attack \u2013 Sql Injection",
    "Infiltration",
    "Heartbleed",
    # Also accept the dash variant
    "Web Attack - Brute Force",
    "Web Attack - XSS",
    "Web Attack - Sql Injection",
}

# Columns that must be non-negative in the raw data
NON_NEGATIVE_COLUMNS = [
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
    "Fwd Packet Length Min",
]

# Critical keys expected in cleaned records (after snake_case normalisation)
CRITICAL_CLEANED_KEYS = [
    "destination_port",
    "label",
    "flow_duration",
    "total_fwd_packets",
]

# Anomaly confidence threshold used by inference.py
ANOMALY_THRESHOLD = 0.80

# Maximum allowed null-rate for critical columns (5%)
MAX_NULL_RATE = 0.05

# Maximum allowed duplicate-row ratio (1%)
MAX_DUPLICATE_RATE = 0.01


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RuleResult:
    """Result of a single quality rule check."""
    rule_name: str
    category: str  # "completeness", "validity", or "integrity"
    passed: bool
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class QualityReport:
    """Aggregate quality report for a pipeline stage."""
    stage: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    passed: bool = True
    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    results: list = field(default_factory=list)

    def add_result(self, result: RuleResult):
        self.results.append(result)
        self.total_rules += 1
        if result.passed:
            self.passed_rules += 1
        else:
            self.failed_rules += 1
            self.passed = False

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"=== Data Quality Report: {self.stage} ===",
            f"Status: {status}",
            f"Timestamp: {self.timestamp}",
            f"Rules: {self.passed_rules}/{self.total_rules} passed",
            "",
        ]
        for r in self.results:
            icon = "✅" if r.passed else "❌"
            lines.append(f"  {icon} [{r.category.upper()}] {r.rule_name}: {r.message}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "results": [
                {
                    "rule_name": r.rule_name,
                    "category": r.category,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
        }


class DataQualityError(Exception):
    """Raised when data quality validation fails, halting the pipeline."""

    def __init__(self, report: QualityReport):
        self.report = report
        super().__init__(report.summary())


# ---------------------------------------------------------------------------
# Stage 1: Raw CSV Validation
# ---------------------------------------------------------------------------

def validate_raw_csv(df: pd.DataFrame) -> QualityReport:
    """
    Validate a raw CICIDS2017 DataFrame loaded from CSV.

    Checks completeness, validity, and integrity rules.
    Raises DataQualityError if any rule fails.

    Parameters
    ----------
    df : pd.DataFrame
        The raw DataFrame read from a CSV file. Column names should be
        stripped of leading/trailing whitespace before calling this function.

    Returns
    -------
    QualityReport
        A report summarising all rule checks.

    Raises
    ------
    DataQualityError
        If one or more quality rules fail.
    """
    report = QualityReport(stage="raw_csv_validation")

    # Strip column names (the CSV has leading spaces)
    df.columns = df.columns.str.strip()

    # ── COMPLETENESS ──────────────────────────────────────────────────

    # C1: Row count minimum – file must contain at least 1 data row
    row_count = len(df)
    report.add_result(RuleResult(
        rule_name="row_count_minimum",
        category="completeness",
        passed=row_count > 0,
        message=f"Dataset contains {row_count} rows" if row_count > 0
                else "Dataset is empty (0 rows)",
        details={"row_count": row_count},
    ))

    # C2: Column count must be exactly 79
    col_count = len(df.columns)
    report.add_result(RuleResult(
        rule_name="column_count_match",
        category="completeness",
        passed=col_count == 79,
        message=f"Column count is {col_count} (expected 79)",
        details={"column_count": col_count, "expected": 79},
    ))

    # C3: Critical columns must be present
    missing_critical = [
        c for c in CRITICAL_COLUMNS_FOR_PIPELINE
        if c not in df.columns
    ]
    report.add_result(RuleResult(
        rule_name="critical_columns_present",
        category="completeness",
        passed=len(missing_critical) == 0,
        message="All critical columns present" if not missing_critical
                else f"Missing critical columns: {missing_critical}",
        details={"missing": missing_critical},
    ))

    # C4: Label column null rate must be <= MAX_NULL_RATE
    if "Label" in df.columns:
        label_null_rate = df["Label"].isna().mean()
        report.add_result(RuleResult(
            rule_name="label_null_rate",
            category="completeness",
            passed=label_null_rate <= MAX_NULL_RATE,
            message=f"Label null rate: {label_null_rate:.4f} (max {MAX_NULL_RATE})",
            details={"null_rate": round(label_null_rate, 6), "threshold": MAX_NULL_RATE},
        ))

    # C5: No fully empty rows (all values NaN/empty)
    fully_empty = df.isna().all(axis=1).sum()
    report.add_result(RuleResult(
        rule_name="no_fully_empty_rows",
        category="completeness",
        passed=fully_empty == 0,
        message=f"No fully empty rows" if fully_empty == 0
                else f"{fully_empty} fully empty rows detected",
        details={"fully_empty_rows": int(fully_empty)},
    ))

    # C6: Destination Port null rate <= MAX_NULL_RATE
    if "Destination Port" in df.columns:
        dp_null_rate = df["Destination Port"].isna().mean()
        report.add_result(RuleResult(
            rule_name="destination_port_null_rate",
            category="completeness",
            passed=dp_null_rate <= MAX_NULL_RATE,
            message=f"Destination Port null rate: {dp_null_rate:.4f} (max {MAX_NULL_RATE})",
            details={"null_rate": round(dp_null_rate, 6), "threshold": MAX_NULL_RATE},
        ))

    # ── VALIDITY ──────────────────────────────────────────────────────

    # V1: Destination Port must be in valid range [0, 65535]
    if "Destination Port" in df.columns:
        port_col = pd.to_numeric(df["Destination Port"], errors="coerce")
        invalid_ports = ((port_col < 0) | (port_col > 65535)).sum()
        # Also count non-numeric values (NaN after coerce minus original NaN)
        coerced_nan = port_col.isna().sum() - df["Destination Port"].isna().sum()
        total_invalid = int(invalid_ports + max(0, coerced_nan))
        report.add_result(RuleResult(
            rule_name="port_range_valid",
            category="validity",
            passed=total_invalid == 0,
            message=f"All ports in valid range [0, 65535]" if total_invalid == 0
                    else f"{total_invalid} rows have invalid port values",
            details={"invalid_count": total_invalid},
        ))

    # V2: Label values must be known CICIDS2017 labels
    if "Label" in df.columns:
        label_values = df["Label"].dropna().str.strip().unique()
        unknown_labels = [lbl for lbl in label_values if lbl not in VALID_LABELS]
        report.add_result(RuleResult(
            rule_name="label_values_valid",
            category="validity",
            passed=len(unknown_labels) == 0,
            message="All labels are valid CICIDS2017 categories" if not unknown_labels
                    else f"Unknown labels found: {unknown_labels}",
            details={"unknown_labels": unknown_labels},
        ))

    # V3: No infinite values in numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_count = 0
    for col in numeric_cols:
        inf_count += np.isinf(df[col].values[~pd.isna(df[col].values)]).sum()
    report.add_result(RuleResult(
        rule_name="no_infinite_values",
        category="validity",
        passed=int(inf_count) == 0,
        message="No infinite values in numeric columns" if inf_count == 0
                else f"{int(inf_count)} infinite values found in numeric columns",
        details={"infinite_count": int(inf_count)},
    ))

    # V4: Non-negative values for packet/flow columns
    negative_issues = {}
    for col in NON_NEGATIVE_COLUMNS:
        if col in df.columns:
            num_col = pd.to_numeric(df[col], errors="coerce")
            neg_count = (num_col < 0).sum()
            if neg_count > 0:
                negative_issues[col] = int(neg_count)
    report.add_result(RuleResult(
        rule_name="non_negative_numerics",
        category="validity",
        passed=len(negative_issues) == 0,
        message="All required columns have non-negative values" if not negative_issues
                else f"Negative values found in: {negative_issues}",
        details={"negative_columns": negative_issues},
    ))

    # ── INTEGRITY ─────────────────────────────────────────────────────

    # I1: Duplicate row ratio must be below threshold
    if row_count > 0:
        dup_count = df.duplicated().sum()
        dup_rate = dup_count / row_count
        report.add_result(RuleResult(
            rule_name="duplicate_row_rate",
            category="integrity",
            passed=dup_rate <= MAX_DUPLICATE_RATE,
            message=f"Duplicate rate: {dup_rate:.4f} ({int(dup_count)} rows) — max {MAX_DUPLICATE_RATE}",
            details={"duplicate_count": int(dup_count), "duplicate_rate": round(dup_rate, 6)},
        ))

    # I2: Expected columns must match the known CICIDS2017 schema
    # We use set-based comparison (ignoring order and duplicate column names)
    expected_set = set(EXPECTED_RAW_COLUMNS)
    actual_set = set(df.columns)
    missing_cols = expected_set - actual_set
    extra_cols = actual_set - expected_set
    schema_match = len(missing_cols) == 0
    report.add_result(RuleResult(
        rule_name="schema_column_match",
        category="integrity",
        passed=schema_match,
        message="Column names match expected CICIDS2017 schema" if schema_match
                else f"Schema mismatch — missing: {missing_cols}, extra: {extra_cols}",
        details={"missing_columns": list(missing_cols), "extra_columns": list(extra_cols)},
    ))

    # ── REPORT ────────────────────────────────────────────────────────
    logger.info(report.summary())

    if not report.passed:
        raise DataQualityError(report)

    return report


# ---------------------------------------------------------------------------
# Stage 2: Cleaned Records Validation
# ---------------------------------------------------------------------------

def validate_cleaned_records(records: list[dict]) -> QualityReport:
    """
    Validate cleaned streaming records (list of dicts from JSONL).

    Parameters
    ----------
    records : list[dict]
        The list of cleaned records, each a dict with snake_case keys.

    Returns
    -------
    QualityReport

    Raises
    ------
    DataQualityError
        If one or more quality rules fail.
    """
    report = QualityReport(stage="cleaned_records_validation")
    total = len(records)

    # ── COMPLETENESS ──────────────────────────────────────────────────

    # C1: Record count minimum
    report.add_result(RuleResult(
        rule_name="record_count_minimum",
        category="completeness",
        passed=total > 0,
        message=f"{total} cleaned records" if total > 0
                else "No cleaned records produced",
        details={"record_count": total},
    ))

    # C2: Critical keys present in every record
    if total > 0:
        missing_keys_count = 0
        records_with_missing = 0
        for rec in records:
            missing = [k for k in CRITICAL_CLEANED_KEYS if k not in rec]
            if missing:
                missing_keys_count += len(missing)
                records_with_missing += 1
        report.add_result(RuleResult(
            rule_name="critical_keys_present",
            category="completeness",
            passed=records_with_missing == 0,
            message="All critical keys present in every record" if records_with_missing == 0
                    else f"{records_with_missing}/{total} records missing critical keys",
            details={"records_with_missing_keys": records_with_missing},
        ))

    # ── VALIDITY ──────────────────────────────────────────────────────

    # V1: All keys must be lowercase with underscores (snake_case)
    if total > 0:
        bad_keys_set = set()
        snake_case_re = re.compile(r"^[a-z0-9][a-z0-9_/]*$")
        for rec in records:
            for key in rec.keys():
                if not snake_case_re.match(key):
                    bad_keys_set.add(key)
        report.add_result(RuleResult(
            rule_name="keys_normalized",
            category="validity",
            passed=len(bad_keys_set) == 0,
            message="All keys are properly normalized (snake_case)" if not bad_keys_set
                    else f"Non-normalized keys found: {bad_keys_set}",
            details={"bad_keys": list(bad_keys_set)},
        ))

    # V2: Port values must be in valid range [0, 65535]
    if total > 0:
        invalid_port_count = 0
        for rec in records:
            port = rec.get("destination_port")
            if port is not None:
                try:
                    p = int(port)
                    if p < 0 or p > 65535:
                        invalid_port_count += 1
                except (ValueError, TypeError):
                    invalid_port_count += 1
        report.add_result(RuleResult(
            rule_name="port_values_valid",
            category="validity",
            passed=invalid_port_count == 0,
            message="All destination ports in valid range" if invalid_port_count == 0
                    else f"{invalid_port_count} records have invalid port values",
            details={"invalid_count": invalid_port_count},
        ))

    # V3: Label values (after cleaning, key is "label") must be valid
    if total > 0:
        # After cleaner's snake_case normalization, label values should be preserved
        unknown = []
        for rec in records:
            lbl = rec.get("label")
            if lbl is not None and str(lbl).strip() not in VALID_LABELS and lbl != 0:
                unknown.append(str(lbl))
        unknown_unique = list(set(unknown))
        report.add_result(RuleResult(
            rule_name="cleaned_label_values_valid",
            category="validity",
            passed=len(unknown_unique) == 0,
            message="All cleaned label values are valid" if not unknown_unique
                    else f"Unknown labels in cleaned data: {unknown_unique}",
            details={"unknown_labels": unknown_unique},
        ))

    # ── INTEGRITY ─────────────────────────────────────────────────────

    # I1: No data corruption — each record should have a reasonable field count
    if total > 0:
        min_expected_fields = 10  # Well below 79 but catches severely corrupted records
        corrupted = sum(1 for rec in records if len(rec) < min_expected_fields)
        report.add_result(RuleResult(
            rule_name="record_field_count",
            category="integrity",
            passed=corrupted == 0,
            message="All records have sufficient fields" if corrupted == 0
                    else f"{corrupted} records have fewer than {min_expected_fields} fields",
            details={"corrupted_records": corrupted, "min_fields": min_expected_fields},
        ))

    # ── REPORT ────────────────────────────────────────────────────────
    logger.info(report.summary())

    if not report.passed:
        raise DataQualityError(report)

    return report


# ---------------------------------------------------------------------------
# Stage 3: Inference Output Validation
# ---------------------------------------------------------------------------

def validate_inference_output(records: list[dict], total_processed: int = 0) -> QualityReport:
    """
    Validate ML inference output records (anomalies published to app-errors).

    Parameters
    ----------
    records : list[dict]
        The list of anomaly/alert records, each a dict.
    total_processed : int
        Total number of records that were evaluated by the inference engine,
        used to verify anomaly-count plausibility.

    Returns
    -------
    QualityReport

    Raises
    ------
    DataQualityError
        If one or more quality rules fail.
    """
    report = QualityReport(stage="inference_output_validation")
    total = len(records)

    # ── COMPLETENESS ──────────────────────────────────────────────────

    # C1: ML metadata fields must be present on every anomaly record
    if total > 0:
        missing_meta = 0
        for rec in records:
            if "ml_confidence_score" not in rec or "ml_model_version" not in rec:
                missing_meta += 1
        report.add_result(RuleResult(
            rule_name="ml_metadata_present",
            category="completeness",
            passed=missing_meta == 0,
            message="All anomaly records have ML metadata" if missing_meta == 0
                    else f"{missing_meta}/{total} records missing ML metadata fields",
            details={"missing_metadata_count": missing_meta},
        ))
    else:
        # Zero anomalies is valid — it just means no threats detected
        report.add_result(RuleResult(
            rule_name="ml_metadata_present",
            category="completeness",
            passed=True,
            message="No anomaly records to validate (0 anomalies detected)",
            details={"record_count": 0},
        ))

    # ── VALIDITY ──────────────────────────────────────────────────────

    # V1: Confidence score must be a float in [0.0, 1.0]
    if total > 0:
        invalid_confidence = 0
        for rec in records:
            score = rec.get("ml_confidence_score")
            if score is not None:
                try:
                    s = float(score)
                    if s < 0.0 or s > 1.0:
                        invalid_confidence += 1
                except (ValueError, TypeError):
                    invalid_confidence += 1
            else:
                invalid_confidence += 1
        report.add_result(RuleResult(
            rule_name="confidence_range_valid",
            category="validity",
            passed=invalid_confidence == 0,
            message="All confidence scores in [0.0, 1.0]" if invalid_confidence == 0
                    else f"{invalid_confidence} records have invalid confidence scores",
            details={"invalid_count": invalid_confidence},
        ))

    # V2: Model version must be a non-empty string
    if total > 0:
        invalid_version = 0
        for rec in records:
            version = rec.get("ml_model_version")
            if not isinstance(version, str) or len(version.strip()) == 0:
                invalid_version += 1
        report.add_result(RuleResult(
            rule_name="model_version_valid",
            category="validity",
            passed=invalid_version == 0,
            message="All records have valid model version strings" if invalid_version == 0
                    else f"{invalid_version} records have invalid model version",
            details={"invalid_count": invalid_version},
        ))

    # V3: All records in the anomaly output must exceed the confidence threshold
    if total > 0:
        below_threshold = 0
        for rec in records:
            score = rec.get("ml_confidence_score")
            if score is not None:
                try:
                    if float(score) <= ANOMALY_THRESHOLD:
                        below_threshold += 1
                except (ValueError, TypeError):
                    pass  # Already caught in V1
        report.add_result(RuleResult(
            rule_name="threshold_consistency",
            category="validity",
            passed=below_threshold == 0,
            message=f"All anomaly records exceed threshold {ANOMALY_THRESHOLD}" if below_threshold == 0
                    else f"{below_threshold} records have confidence <= {ANOMALY_THRESHOLD}",
            details={"below_threshold_count": below_threshold, "threshold": ANOMALY_THRESHOLD},
        ))

    # ── INTEGRITY ─────────────────────────────────────────────────────

    # I1: Anomaly count must be <= total records processed
    if total_processed > 0:
        plausible = total <= total_processed
        report.add_result(RuleResult(
            rule_name="anomaly_count_plausible",
            category="integrity",
            passed=plausible,
            message=f"{total} anomalies out of {total_processed} processed — plausible" if plausible
                    else f"{total} anomalies exceeds {total_processed} total processed records",
            details={"anomaly_count": total, "total_processed": total_processed},
        ))

    # ── REPORT ────────────────────────────────────────────────────────
    logger.info(report.summary())

    if not report.passed:
        raise DataQualityError(report)

    return report
