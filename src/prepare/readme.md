# Data Preparation Pipeline (`src/prepare`)

يقوم هذا المجلد بإدارة عمليات معالجة السجلات وتجهيز البيانات لتدريب نماذج كشف الهجمات الشبكية مع ضمان خلو البيانات من أي Data Leakage.

---

## Files Overview

| File | Description |
| :--- | :--- |
| **`prepare_data.py`** | يقراء سجلات `JSONL` الخام، واستخراج الميزات الهندسية مع إسقاط الحقول الحساسة، وتحويلها إلى صيغة `Parquet`. |
| **`balance_parquet.py`** | يقوم بإجراء **Under-sampling** مقتصد للذاكرة (Streaming) لموازنة فئتي `BENIGN` و `ATTACK` بنفس النسبة (1:1). |

---

## File Paths & Storage Layout

جميع ملفات البيانات المعالجة والمُصدرة تُخزن تحت المسار: **`data/exports/`**

* **`raw_jsonl`**: `root / "data" / "exports" / "cleaned_logs.jsonl"`
* **`prepared_parquet`**: `root / "data" / "exports" / "cleaned_logs.parquet"`
* **`balanced_parquet`**: `root / "data" / "exports" / "cleaned_logs_balanced.parquet.parquet"`

---

## Execution Sequence

### 1. Transform JSONL Logs to Parquet
```bash
python -m src.prepare.prepare_data

### 2. Doing UnderSampling for parquet
```bash
python -m src.prepare.balance_parquet.py