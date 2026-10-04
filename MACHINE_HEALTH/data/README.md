# Machine Health Data Directory

This directory contains test datasets, schema descriptions, and data provenance documentation for the vibration condition monitoring module.

---

## 📄 Datasets

### 1. `sample_vibration_test_data.csv` (Committed)
- **Size:** ~9.5 KB (120 rows, 9 columns)
- **Purpose:** Standalone test suite input for validating the serialized anomaly detection pipeline (`outputs/models/baseline_anomaly_detector.joblib`) without downloading external datasets.
- **Scenarios:**
  - `normal` (60 windows): Simulated baseline vibration telemetry.
  - `elevated_vibration` (30 windows): Moderate increase in continuous vibration energy and RMS.
  - `severe_anomaly` (30 windows): High peak acceleration, high kurtosis, and severe transient shocks.
- **Columns:**
  - `sample_id` *(metadata)*: Unique window identifier (e.g., `NOR_001`, `SEV_025`).
  - `mean`, `std`, `rms`, `peak`, `crest_factor`, `kurtosis` *(sensor telemetry)*: 6 core statistical features extracted from high-frequency accelerometer channels.
  - `expected_scenario` *(metadata)*: Ground truth scenario label for test scoring.
  - `is_synthetic` *(metadata)*: Boolean flag confirming synthetic origin.

---

### 2. `all_vibration_features.csv` (Full Dataset — Excluded from Git Tracking)
- **Size:** ~24.7 MB (130,232 observation windows, 1,040 recordings)
- **Provenance:** Paderborn University Bearing Data Set (K001–K006 healthy reference bearings; KA/KB/KI artificially damaged bearings with inner/outer raceway electrical discharge and drilling defects).
- **Sampling & Windowing:**
  - Raw accelerometer sampling rate: 64 kHz.
  - Window size: 4,096 samples (~64 ms per window, 50% overlap).
- **Why excluded from Git:**
  In accordance with Git repository best practices, large intermediate datasets (>20 MB) are excluded from direct version control to avoid repository bloat.
- **How to obtain or regenerate:**
  1. The full dataset can be re-extracted from the raw Paderborn `.mat` archive files using the signal processing routines documented in [`notebooks/bearing_health_model_development.ipynb`](../notebooks/bearing_health_model_development.ipynb).
  2. For team members working on local model training, place `all_vibration_features.csv` directly into the `MACHINE_HEALTH/` root or data folder before running full training loops.
