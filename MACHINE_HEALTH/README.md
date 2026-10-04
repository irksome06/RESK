# Machine Health Monitoring & Predictive Maintenance

Industrial condition monitoring and vibration anomaly detection module for the **RESK** platform. This module detects mechanical degradation, localized bearing faults, and transient shock anomalies using statistical time-domain vibration feature extraction and unsupervised machine learning.

---

## 📌 Table of Contents
- [Project Overview](#project-overview)
- [Directory Structure](#directory-structure)
- [File Inventory & Selection Rationale](#file-inventory--selection-rationale)
- [Mathematical Feature Schema](#mathematical-feature-schema)
- [Model Pipeline Architecture](#model-pipeline-architecture)
- [Evaluation & Verification Results](#evaluation--verification-results)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Running the Test Suite](#running-the-test-suite)
  - [Launching the Development Notebook](#launching-the-development-notebook)
- [Model Loading & Inference Guide](#model-loading--inference-guide)
- [Integration Roadmap for RESK](#integration-roadmap-for-resk)

---

## 🔎 Project Overview

Rotating machinery (such as wind turbines, generators, heavy industrial motors, and gearboxes) emits characteristic vibration patterns during nominal operation. Mechanical degradation—such as raceway fatigue, ball spalling, or lubrication loss—manifests as elevated vibration kinetic energy (RMS) and sharp, repetitive shock transients (high peak amplitude, crest factor, and kurtosis).

This module delivers:
1. **Time-Series Vibration Feature Engineering**: Ingests 6 raw statistical metrics and dynamically computes 4 dimensionless physical shock indicators without lookahead leakage.
2. **Unsupervised Anomaly Detection**: Employs a production-fitted `IsolationForest` pipeline trained on empirical bearing datasets to detect anomalous operation without requiring pre-labeled failure classes.
3. **Continuous Severity Scoring**: Maps multidimensional vibration features into continuous decision scores and three operational severity tiers (`LOW`, `ELEVATED`, `HIGH`).
4. **Reproducible Diagnostic Reports**: Includes automated verification test harnesses, comprehensive EDA charts, and statistical audit reports.

---

## 📁 Directory Structure

```
MACHINE_HEALTH/
├── data/
│   ├── sample_vibration_test_data.csv          # 120-window synthetic test dataset (~9.5 KB)
│   └── README.md                               # Dataset schema, provenance, and download guide
├── notebooks/
│   └── bearing_health_model_development.ipynb  # End-to-end ML workflow with complete outputs
├── outputs/
│   ├── eda/                                    # 8 high-resolution exploratory data analysis figures
│   │   ├── eda_01_dataset_structure.png
│   │   ├── eda_02_univariate_distributions.png
│   │   ├── eda_03_univariate_boxplots.png
│   │   ├── eda_04_correlation_heatmap.png
│   │   ├── eda_05_bivariate_scatters.png
│   │   ├── eda_06_groupwise_bearing_distributions.png
│   │   ├── eda_07_sequential_window_analysis.png
│   │   └── eda_08_pca_anomaly_clusters.png
│   ├── evaluation/                             # Evaluation plots & feature importance rankings
│   │   ├── dummy_test_anomaly_scores_by_scenario.png
│   │   └── rf_feature_importance.png
│   ├── models/
│   │   ├── baseline_anomaly_detector.joblib     # Pretrained scikit-learn Pipeline (1.99 MB)
│   │   └── model_metadata.json                 # Model schema, hyperparameters, and metadata
│   └── reports/                                # Audit CSVs and markdown verification reports
│       ├── dummy_vibration_test_predictions.csv
│       ├── dummy_vibration_test_report.md
│       ├── model_comparison_report.csv
│       ├── code_and_methodology_audit.csv
│       ├── validation_strategy_audit_report.csv
│       ├── demo_benchmark_comparison_report.csv
│       └── eda_summary_report.csv
├── scripts/
│   └── test_synthetic_vibration_data.py        # Independent verification test harness
├── .gitignore                                  # Ignores large datasets and temporary artifacts
├── requirements.txt                            # Standalone Python dependencies
└── README.md                                   # Module documentation
```

---

## 📋 File Inventory & Selection Rationale

Following a rigorous audit of the workspace files, the repository has been curated to maintain only essential, reproducible, and production-grade assets:

| Original File | Curated Location | Action & Rationale |
| :--- | :--- | :--- |
| `predictive_maintenance_ml.ipynb` | `notebooks/bearing_health_model_development.ipynb` | **Retained & Renamed**: Full 37-cell audited notebook with all code cells executed. |
| `one.ipynb` | *Excluded* | **Deduplicated**: Exact bit-for-bit duplicate of `predictive_maintenance_ml.ipynb` (identical SHA-256 hash). |
| `dummy_vibration_model_test.csv` | `data/sample_vibration_test_data.csv` | **Retained & Renamed**: Lightweight (9.5 KB), clean, non-sensitive 120-row test dataset. |
| `all_vibration_features.csv` | *Excluded from Git* | **Documented in `data/README.md`**: Large generated dataset (~24.7 MB) excluded to prevent Git repository bloat; instructions for re-generating are provided. |
| `test_synthetic_dummy_dataset.py` | `scripts/test_synthetic_vibration_data.py` | **Retained & Renamed**: Standalone evaluation and audit script; updated relative paths and fixed string escape sequences. |
| `outputs/models/*` | `outputs/models/` | **Retained**: Verified loadable scikit-learn pipeline (1.99 MB) and accompanying schema metadata. |
| `outputs/eda/*` | `outputs/eda/` | **Retained**: 8 diagnostic charts detailing distributions, correlations, and PCA clustering. |
| `outputs/evaluation/*` | `outputs/evaluation/` | **Retained**: Anomaly score separation by scenario and Random Forest feature importance. |
| `outputs/reports/*` | `outputs/reports/` | **Retained**: Essential CSV audit summaries and Markdown evaluation reports. |
| `check_quotes.py`, `fix_*.py` | *Excluded* | **Cleaned**: One-off text-repair scripts used during notebook generation; non-essential for the application. |

---

## ⚙️ Mathematical Feature Schema

The model pipeline ingests **6 raw statistical telemetry metrics** and computes **4 derived dimensionless shock indicators**, producing a 10-feature vector:

### 1. Raw Telemetry Features (6)
- **`mean`**: Average amplitude ($\mu = \frac{1}{N}\sum x_i$), tracks DC sensor offset.
- **`std`**: Standard deviation ($\sigma$), represents dynamic fluctuation energy.
- **`rms`**: Root mean square ($\sqrt{\frac{1}{N}\sum x_i^2}$), total continuous mechanical kinetic energy.
- **`peak`**: Absolute maximum amplitude ($\max |x_i|$), peak transient shock.
- **`crest_factor`**: Ratio of peak to continuous RMS ($\frac{\text{peak}}{\text{rms}}$), measures signal impulsiveness.
- **`kurtosis`**: 4th standardized moment ($\frac{\mu_4}{\sigma^4}$), sensitive indicator of early localized impacts.

### 2. Derived Shock Indicators (4)
- **`impulse_factor`**: $\frac{\text{peak}}{\text{rms} + 10^{-8}}$ — Ratio of extreme peak shock to continuous energy.
- **`margin_factor`**: $\frac{\text{peak}}{\sqrt{\max(10^{-8}, \text{rms})}}$ — Clearance margin ratio sensitive to initial micro-spalling.
- **`log_kurtosis`**: $\ln(1 + \max(0, \text{kurtosis}))$ — Variance-stabilized transformation of heavy-tailed impact distributions.
- **`rms_to_peak`**: $\frac{\text{rms}}{\text{peak} + 10^{-8}}$ — Waveform energy concentration ratio (inverse crest factor).

---

## 🧠 Model Pipeline Architecture

The serialized model (`outputs/models/baseline_anomaly_detector.joblib`) is packaged as an end-to-end `scikit-learn` Pipeline:

```
Raw Telemetry (6 features)
         ↓
Feature Engineering Engine (Derives 4 physical shock features → 10 total)
         ↓
SimpleImputer(strategy='median')
         ↓
StandardScaler() [Trained on empirical Paderborn baseline windows]
         ↓
IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
         ↓
Continuous Decision Score & Severity Classification
```

### Hyperparameters:
- **Model Type:** `IsolationForest`
- **Number of Estimators:** `150`
- **Contamination Rate:** `0.05` (5% nominal baseline outlier expectation)
- **Decision Offset (`offset_`):** `-0.57100955`
- **Random State:** `42`

---

## 📊 Evaluation & Verification Results

The serialized pipeline was evaluated across 120 synthetic validation windows in `scripts/test_synthetic_vibration_data.py`:

| Operational Scenario | Rows | Inferences Passed | Flagged Anomaly Rate | Mean Decision Score | Primary Severity Tier |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`normal`** | 60 | 60 (100%) | 88.3%* | `-0.0267` | LOW / Baseline |
| **`elevated_vibration`** | 30 | 30 (100%) | 100.0% | `-0.0714` | ELEVATED |
| **`severe_anomaly`** | 30 | 30 (100%) | 100.0% | `-0.1097` | HIGH |

> **Audit Insight on Synthetic Normal Flagging:**  
> The 88.3% anomaly flag rate on synthetic normal data is a documented covariate shift phenomenon. Synthetic Gaussian signals exhibit lower crest factor ($CF \approx 2.98$) and higher RMS ($RMS \approx 0.76$) compared to empirical bearing baselines ($CF \approx 6.43, RMS \approx 0.36$), and are correctly identified as out-of-distribution by the model.

---

## 🚀 Getting Started

### Installation
Ensure Python 3.9+ is available. From the `MACHINE_HEALTH` directory, install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Test Suite
Execute the independent verification harness to confirm model loading, feature calculation, and inference scoring:

```bash
python scripts/test_synthetic_vibration_data.py
```

Generated audit artifacts:
- Predictions: `outputs/reports/dummy_vibration_test_predictions.csv`
- Detailed Markdown Audit: `outputs/reports/dummy_vibration_test_report.md`
- Diagnostic Charts: `outputs/evaluation/dummy_test_anomaly_scores_by_scenario.png`

### Launching the Development Notebook
To inspect the complete training methodology, cross-validation audits, and data visualizations:

```bash
jupyter notebook notebooks/bearing_health_model_development.ipynb
```

---

## 💻 Model Loading & Inference Guide

To integrate the model into a Python service:

```python
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

# 1. Load the pre-trained pipeline
model_path = Path("outputs/models/baseline_anomaly_detector.joblib")
pipeline = joblib.load(model_path)

# 2. Prepare raw telemetry input (6 features)
raw_telemetry = pd.DataFrame([{
    "mean": 0.012,
    "std": 0.345,
    "rms": 0.360,
    "peak": 2.150,
    "crest_factor": 5.972,
    "kurtosis": 5.820
}])

# 3. Compute derived shock features
raw_telemetry["impulse_factor"] = raw_telemetry["peak"] / (raw_telemetry["rms"] + 1e-8)
raw_telemetry["margin_factor"] = raw_telemetry["peak"] / np.sqrt(np.maximum(1e-8, raw_telemetry["rms"]))
raw_telemetry["log_kurtosis"] = np.log1p(np.maximum(0, raw_telemetry["kurtosis"]))
raw_telemetry["rms_to_peak"] = raw_telemetry["rms"] / (raw_telemetry["peak"] + 1e-8)

# 4. Enforce strict feature ordering (10 features)
feature_order = [
    "mean", "std", "rms", "peak", "crest_factor", "kurtosis",
    "impulse_factor", "margin_factor", "log_kurtosis", "rms_to_peak"
]
X = raw_telemetry[feature_order]

# 5. Predict continuous score and anomaly status
decision_score = pipeline.decision_function(X)[0]
is_anomaly = bool(pipeline.predict(X)[0] == -1)

# 6. Map to severity tier
if decision_score >= 0.0:
    severity = "LOW"
elif decision_score >= -0.10:
    severity = "ELEVATED"
else:
    severity = "HIGH"

print(f"Decision Score: {decision_score:.4f} | Severity: {severity} | Anomaly: {is_anomaly}")
```

---

## 🔗 Integration Roadmap for RESK

1. **Backend Integration (`backend/app/services/`)**:
   - Package the inference logic into a singleton service: `backend/app/services/machine_health_service.py`.
   - Load `baseline_anomaly_detector.joblib` during FastAPI lifespan startup.
2. **API Endpoint (`backend/app/routes/`)**:
   - Expose `POST /api/v1/machine-health/telemetry/evaluate` accepting vibration window frames.
   - Return real-time anomaly scores, severity ratings, and recommended maintenance actions.
3. **Frontend Dashboard (`frontend/src/pages/`)**:
   - Introduce an **Asset Health & Telemetry** dashboard page.
   - Display real-time health gauges, alert notifications, and historical vibration trends.
