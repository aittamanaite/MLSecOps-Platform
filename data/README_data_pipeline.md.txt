# Data Pipeline Execution Guide

## 1. Input Data Setup
- **Raw Dataset Path:** `/data/raw`
- **Download Link:** [Google Drive Raw Datasets](https://drive.google.com/drive/folders/11Pv-TauVhMHxH5Th3SaKvvU9HLuYL1rC)

## 2. Pipeline Execution
1. Spin up the docker containers for **Dagster** and **Redpanda**.
2. Open the **Dagster UI**, navigate to configuration, and activate the required **sensor**.
3. Trigger and run the target job(s).

## 3. Expected Output
Upon successful pipeline completion:
- **Cleaned Data Directory:** `/data/exports/`
- **File Format:** `.jsonl` (JSON Lines)