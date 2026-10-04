# Machine Health & Vibration Anomaly Detection

Industrial-grade predictive maintenance and condition monitoring module for the RESK platform. This module detects mechanical degradation, shock anomalies, and bearing faults using time- and frequency-domain vibration signal analysis and unsupervised anomaly detection models.

---

## 📌 Table of Contents
- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Feature Engineering Schema](#feature-engineering-schema)
- [Model Pipeline Architecture](#model-pipeline-architecture)
- [Evaluation & Verification](#evaluation--verification)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Running the Test Suite](#running-the-test-suite)
  - [Running the Notebooks](#running-the-notebooks)
- [Integration Roadmap](#integration-roadmap)

---

## 🔎 Overview

Rotating machinery (turbines, generators, motors, gearboxes) emits characteristic vibration patterns during normal operation. As mechanical wear occurs (spalling, race defects, lubrication failure), continuous vibration energy and transient shock impacts deviate significantly from baseline behavior.

This module provides:
1. **Feature Engineering**: Derivation of statistical and physical vibration metrics over time-series windows.
2. **Unsupervised Anomaly Detection**: An `IsolationForest` pipeline trained on empirical bearing datasets to detect out-of-distribution mechanical anomalies without requiring labeled failure events.
3. **Continuous Severity Scoring**: Quantitative decision functions that map vibration telemetry into severity tiers (`NORMAL`, `ELEVATED`, `SEVERE`).
4. **Verification & Audit Reports**: Automated test suites evaluating the model against known degradation scenarios.

---

## 📁 Directory Structure

```
machine_health/
├── data/
│   └── dummy_vibration_model_test.csv      # 120-window synthetic evaluation dataset
├── outputs/
│   ├── eda/                                # Exploratory data analysis charts (heatmaps, PCA, boxplots)
│   ├── evaluation/                         # Scenario decision score distributions & feature importances
│   ├── models/
│   │   ├── baseline_anomaly_detector.joblib # Serialized scikit-learn model pipeline
│   │   └── model_metadata.json             # Feature schema, hyperparameters, and pipeline metadata
│   └── reports/                            # Performance summaries, prediction CSVs, and audit reports
├── all_vibration_features.csv              # Extracted baseline vibration feature matrix (~24.7 MB)
├── predictive_maintenance_ml.ipynb         # Full ML notebook: EDA, training, evaluation, and serialization
├── one.ipynb                               # Alternative exploratory workflow notebook
├── test_synthetic_dummy_dataset.py         # Verification test harness for serialized model inference
├── generate_notebook.py                    # Script to programmatically generate reproducible notebooks
├── execute_notebook.py                     # Headless notebook execution runner
└── update_one_notebook.py                  # Notebook cell updater utility
```

---

## ⚙️ Feature Engineering Schema

The model pipeline operates on **10 statistical and physical vibration features**. The ingestion service accepts 6 raw statistics and dynamically calculates 4 physical shock indicators:

### 1. Raw Telemetry Features (6)
| Feature | Description | Physical Significance |
| :--- | :--- | :--- |
| `mean` | Average amplitude | Baseline DC offset or sensor bias |
| `std` | Standard deviation | Dynamic vibration energy spread |
| `rms` | Root mean square | Total continuous mechanical kinetic energy |
| `peak` | Absolute maximum amplitude | Peak transient shock or impact |
| `crest_factor` | $\frac{\text{peak}}{\text{rms}}$ | Impulsiveness of waveform (early indicator of localized faults) |
| `kurtosis` | 4th standardized moment | Measure of peakedness / heavy-tailed transient impact density |

### 2. Derived Shock Indicators (4)
| Feature | Formula | Engineering Context |
| :--- | :--- | :--- |
| `impulse_factor` | $\frac{\text{peak}}{\text{rms} + 10^{-8}}$ | Ratio of extreme shock to continuous vibration energy |
| `margin_factor` | $\frac{\text{peak}}{\sqrt{\max(10^{-8}, \text{rms})}}$ | Clearance margin ratio; sensitive to micro-cracks |
| `log_kurtosis` | $\ln(1 + \max(0, \text{kurtosis}))$ | Variance-stabilized logarithmic transformation of impact kurtosis |
| `rms_to_peak` | $\frac{\text{rms}}{\text{peak} + 10^{-8}}$ | Inverse crest factor / waveform energy concentration |

---

## 🧠 Model Pipeline Architecture

The serialized model (`outputs/models/baseline_anomaly_detector.joblib`) is packaged as an end-to-end `scikit-learn` Pipeline:

```
Raw Input (6 Features)
         ↓
Feature Derivation Engine (10 Features)
         ↓
SimpleImputer(strategy='median')
         ↓
StandardScaler() [Empirical Baseline Means & Variances]
         ↓
IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
         ↓
Continuous Decision Score & Binary Anomaly Classification
```

### Hyperparameters:
- **Algorithm:** Isolation Forest
- **Estimators (`n_estimators`):** `150`
- **Contamination Rate:** `0.05` (assumes 5% baseline operational anomaly threshold)
- **Decision Offset (`offset_`):** `-0.57100955`

---

## 📊 Evaluation & Verification

The model was audited using `test_synthetic_dummy_dataset.py` against 120 synthetic operational windows:

| Scenario | Total Windows | Anomaly Rate | Mean Decision Score | Severity Profile |
| :--- | :---: | :---: | :---: | :--- |
| **Normal Operation** | 60 | 88.3%* | `-0.0267` | Mild / Baseline |
| **Elevated Vibration** | 30 | 100.0% | `-0.0714` | Moderate Degradation |
| **Severe Anomaly** | 30 | 100.0% | `-0.1097` | Critical Impending Failure |

> *\*Note on Synthetic Normal Distribution*: The high flagged rate on synthetic normal data is documented in [`outputs/reports/dummy_vibration_test_report.md`](outputs/reports/dummy_vibration_test_report.md) — synthetic Gaussian noise generators produce lower crest factors ($CF \approx 2.98$) compared to empirical industrial bearing baselines ($CF \approx 6.43$), correctly identified as out-of-distribution by the model.

---

## 🚀 Getting Started

### Prerequisites
Make sure Python 3.9+ is installed. Install required data science packages:

```bash
pip install numpy pandas scikit-learn joblib matplotlib seaborn jupyter
```

### Running the Test Suite
To verify the serialized model and generate predictions on the dummy test dataset:

```bash
cd machine_health
python test_synthetic_dummy_dataset.py
```

Outputs will be generated in:
- `outputs/reports/dummy_vibration_test_predictions.csv`
- `outputs/reports/dummy_vibration_test_report.md`
- `outputs/evaluation/dummy_test_anomaly_scores_by_scenario.png`

### Running the Notebooks
To explore data distributions, train new models, or inspect visualizations:

```bash
cd machine_health
jupyter notebook predictive_maintenance_ml.ipynb
```

---

## 🔗 Integration Roadmap (RESK Platform)

- [ ] **Backend Service**: Create `backend/app/services/machine_health_service.py` to load `baseline_anomaly_detector.joblib` into memory on startup.
- [ ] **API Endpoint**: Expose `POST /api/v1/machine-health/predict` accepting JSON telemetry windows and returning health scores and anomaly flags.
- [ ] **Frontend Widget**: Build a real-time vibration dashboard in `frontend/src/pages/` displaying health gauges, FFT frequency plots, and anomaly alert logs.
