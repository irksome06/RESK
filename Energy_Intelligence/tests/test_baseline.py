"""
Phase 8.1 Energy Baseline Modeling Test Suite (V2).
Validates:
1. Dataset generation
2. Dataset persistence (data/raw and data/processed)
3. Target calculation (per-machine cumulative meter delta)
4. Per-machine chronological ordering & initial record handling
5. Negative energy delta handling & exclusion
6. Feature exclusion (EXCLUDED_FEATURES)
7. No power_kw in V2 feature list
8. No energy_kwh in V2 feature list
9. No current_a in V2 feature list
10. Chronological train/test split (80/20)
11. TimeSeriesSplit configuration
12. Pipeline fitting
13. Model training and evaluation
14. Model artifact creation (V2 and default)
15. Metadata creation with complete audit trail
16. Prediction endpoint
17. Prediction without power_kw
18. Prediction without energy_kwh
19. Expected-energy positivity/sanity
20. Energy deviation calculation
21. Zero expected-energy handling
22. Representative state predictions (SLEEP < IDLE < RUNNING)
23. Reproducibility with deterministic random seed
24. Model loading from disk
25. Feature-order consistency
26. Leakage audit
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from fastapi.testclient import TestClient

# Ensure person3_energy_intelligence is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from api.main import app
from database.schemas import TelemetryRecord, MachineState
from ml.preprocessing import (
    extract_features_and_target_from_records,
    create_preprocessor,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    ALL_FEATURE_COLUMNS,
    EXCLUDED_FEATURES,
    TARGET_COLUMN,
)
from ml.baseline_models import get_candidate_models, XGBOOST_AVAILABLE
from ml.baseline import EnergyBaselineService, predict_expected_energy
from ml.train import (
    generate_and_persist_baseline_dataset,
    calculate_energy_deviation,
    train_and_select_baseline,
)

client = TestClient(app)

MODELS_DIR = BASE_DIR / "models"
V2_MODEL_PATH = MODELS_DIR / "energy_baseline_v2_production_aware.joblib"
DEFAULT_MODEL_PATH = MODELS_DIR / "energy_baseline.joblib"
METADATA_PATH = MODELS_DIR / "energy_baseline_metadata.json"
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "factory_telemetry.csv"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "baseline_training_data.csv"


# Helper to build synthetic sequential telemetry records
def create_sample_telemetry_series(count: int = 20, reset_at: int = -1, machine_id: str = "M01"):
    records = []
    base_time = datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc)
    cum_energy = 100.0
    cum_prod = 0

    for i in range(count):
        t = base_time + timedelta(seconds=i * 2)
        if i == reset_at:
            cum_energy = 10.0  # meter drop/reset
        else:
            cum_energy += 0.005

        if i % 3 == 0:
            state = MachineState.RUNNING
            power = 9.0
            prod_delta = 1
        elif i % 3 == 1:
            state = MachineState.IDLE
            power = 1.2
            prod_delta = 0
        else:
            state = MachineState.RUNNING
            power = 9.2
            prod_delta = 1

        cum_prod += prod_delta

        rec = TelemetryRecord(
            timestamp=t,
            machine_id=machine_id,
            machine_state=state,
            power_kw=power,
            energy_kwh=round(cum_energy, 4),
            production_count=cum_prod,
            production_delta=prod_delta,
            rpm=1450.0 if state == MachineState.RUNNING else 0.0,
            temperature_c=55.0,
            vibration=0.22,
            torque_nm=30.0 if state == MachineState.RUNNING else 0.0,
            voltage_v=415.0,
            current_a=14.0 if state == MachineState.RUNNING else 2.0,
            health_score=98.5,
            anomaly_score=0.02,
        )
        records.append(rec)
    return records


# ==============================================================================
# 1. DATASET & TARGET TESTS
# ==============================================================================

def test_dataset_generation():
    """Requirement 1: Verify dataset generation returns raw and processed datasets."""
    df_raw, df_proc = generate_and_persist_baseline_dataset(cycles=1, steps_per_phase=5)
    assert len(df_raw) > 0
    assert len(df_proc) > 0
    assert TARGET_COLUMN in df_proc.columns


def test_dataset_persistence():
    """Requirement 2: Verify raw and processed datasets are saved to disk."""
    assert RAW_DATA_PATH.exists(), f"Raw data CSV missing at {RAW_DATA_PATH}"
    assert PROCESSED_DATA_PATH.exists(), f"Processed data CSV missing at {PROCESSED_DATA_PATH}"
    df_proc = pd.read_csv(PROCESSED_DATA_PATH)
    assert len(df_proc) > 100
    assert TARGET_COLUMN in df_proc.columns


def test_target_calculation():
    """Requirement 3: Verify target interval_energy_kwh is calculated as E[t] - E[t-1]."""
    records = create_sample_telemetry_series(count=5)
    df = extract_features_and_target_from_records(records)
    target = df[TARGET_COLUMN]

    assert len(df) == 4  # 5 records produce 4 intervals
    assert len(target) == 4
    for val in target:
        assert np.isclose(val, 0.005, atol=1e-4)


def test_per_machine_chronological_ordering():
    """Requirement 4: Verify initial record per machine is dropped and chronological order is preserved."""
    recs_m1 = create_sample_telemetry_series(count=5, machine_id="M01")
    recs_m2 = create_sample_telemetry_series(count=5, machine_id="M02")
    combined = recs_m1 + recs_m2

    df = extract_features_and_target_from_records(combined)
    # Each machine of 5 records contributes 4 intervals = 8 total intervals
    assert len(df) == 8
    # Must be sorted chronologically
    timestamps = pd.to_datetime(df["timestamp"])
    assert (timestamps.diff().dropna() >= pd.Timedelta(0)).all()


def test_negative_energy_delta_handling():
    """Requirement 5: Verify non-monotonic meter drops/resets are excluded, not converted to false zero."""
    records = create_sample_telemetry_series(count=10, reset_at=5)
    df = extract_features_and_target_from_records(records)
    target = df[TARGET_COLUMN]

    # Record 5 reset excluded
    assert len(df) == 8
    for val in target:
        assert val > 0.0


# ==============================================================================
# 2. FEATURE EXCLUSION TESTS
# ==============================================================================

def test_feature_exclusion():
    """Requirement 6: Verify all EXCLUDED_FEATURES are absent from ALL_FEATURE_COLUMNS."""
    for feat in EXCLUDED_FEATURES:
        assert feat not in ALL_FEATURE_COLUMNS, f"Forbidden feature {feat} present in ALL_FEATURE_COLUMNS!"


def test_no_power_kw_in_v2_features():
    """Requirement 7: Explicit check that power_kw is NOT a model feature."""
    assert "power_kw" not in ALL_FEATURE_COLUMNS


def test_no_energy_kwh_in_v2_features():
    """Requirement 8: Explicit check that energy_kwh is NOT a model feature."""
    assert "energy_kwh" not in ALL_FEATURE_COLUMNS


def test_no_current_a_in_v2_features():
    """Requirement 9: Explicit check that current_a is NOT a model feature."""
    assert "current_a" not in ALL_FEATURE_COLUMNS


# ==============================================================================
# 3. TIME-SERIES VALIDATION & LEAKAGE AUDIT TESTS
# ==============================================================================

def test_chronological_train_test_split():
    """Requirement 10: Verify 80/20 train/test split maintains strict chronological boundary."""
    records = create_sample_telemetry_series(count=50)
    df = extract_features_and_target_from_records(records)

    split_idx = int(len(df) * 0.8)
    df_train = df.iloc[:split_idx]
    df_test = df.iloc[split_idx:]

    assert df_train.index.max() < df_test.index.min()
    assert df_train["timestamp"].max() <= df_test["timestamp"].min()


def test_time_series_split_configuration():
    """Requirement 11: Verify TimeSeriesSplit operates strictly chronologically without lookahead."""
    tscv = TimeSeriesSplit(n_splits=5)
    indices = np.arange(100)

    for train_idx, val_idx in tscv.split(indices):
        assert max(train_idx) < min(val_idx)
        assert len(train_idx) > 0
        assert len(val_idx) > 0


def test_pipeline_fitting():
    """Requirement 12: Verify full ColumnTransformer pipeline fits cleanly without electrical proxies."""
    from sklearn.linear_model import Ridge
    preprocessor = create_preprocessor()
    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", Ridge(alpha=1.0)),
    ])

    records = create_sample_telemetry_series(count=15)
    df = extract_features_and_target_from_records(records)
    X = df[ALL_FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    pipe.fit(X, y)
    preds = pipe.predict(X)
    assert len(preds) == len(y)
    assert not np.isnan(preds).any()


def test_model_training():
    """Requirement 13: Verify train_and_select_baseline executes and selects a winning model."""
    summary = train_and_select_baseline(save_artifacts=False)
    assert "selected_model" in summary
    assert "model_version" in summary
    assert summary["model_version"] == "v2_production_aware"
    assert "cv_metrics" in summary
    assert summary["cv_metrics"]["cv_mae"] > 0.0


# ==============================================================================
# 4. ARTIFACTS & INFERENCE TESTS
# ==============================================================================

def test_model_artifact_creation():
    """Requirement 14: Verify V2 model artifact is saved on disk."""
    assert V2_MODEL_PATH.exists(), f"V2 model artifact missing at {V2_MODEL_PATH}"
    assert DEFAULT_MODEL_PATH.exists(), f"Default model artifact missing at {DEFAULT_MODEL_PATH}"


def test_metadata_creation():
    """Requirement 15: Verify baseline metadata contains complete experiment audit trail."""
    with open(METADATA_PATH, "r") as f:
        meta = json.load(f)

    assert meta["model_version"] == "v2_production_aware"
    assert "excluded_features" in meta
    assert "power_kw" in meta["excluded_features"]
    assert "energy_kwh" in meta["excluded_features"]
    assert "current_a" in meta["excluded_features"]
    assert "cv_metrics" in meta
    assert "test_metrics" in meta
    assert "machine_profiles" in meta
    assert meta["machine_profiles"]["M01"]["name"] == "CNC Milling Center 1"
    assert meta["machine_profiles"]["M02"]["name"] == "Heavy Lathe 2"
    assert meta["machine_profiles"]["M03"]["name"] == "Stamping Press 3"
    assert meta["machine_profiles"]["M04"]["name"] == "Precision Grinder 4"


def test_prediction_endpoint():
    """Requirement 16: Verify POST /baseline/predict returns expected schema and value."""
    payload = {
        "machine_id": "M01",
        "machine_state": "RUNNING",
        "production_delta": 2,
        "production_rate": 120.0,
        "rpm": 1450.0,
        "torque_nm": 30.0,
        "temperature_c": 48.0,
        "vibration": 0.18,
        "health_score": 95.0,
        "anomaly_score": 0.02,
        "dt_seconds": 60.0,
        "hour_of_day": 14.0,
        "day_of_week": 2.0,
    }
    response = client.post("/baseline/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "expected_energy_kwh" in data
    assert data["expected_energy_kwh"] >= 0.0
    assert data["model_version"] == "v2_production_aware"
    assert "power_kw" not in data["features_used"]


def test_prediction_without_power_kw():
    """Requirement 17: Verify prediction succeeds without providing power_kw."""
    payload = {
        "machine_id": "M01",
        "machine_state": "RUNNING",
        "production_delta": 1,
        "rpm": 1450.0,
        "dt_seconds": 2.0,
    }
    # No power_kw supplied
    res = predict_expected_energy(payload)
    assert res["expected_energy_kwh"] >= 0.0
    assert "power_kw" not in res["features_used"]


def test_prediction_without_energy_kwh():
    """Requirement 18: Verify prediction succeeds without providing energy_kwh."""
    payload = {
        "machine_id": "M02",
        "machine_state": "IDLE",
        "production_delta": 0,
        "rpm": 20.0,
        "dt_seconds": 2.0,
    }
    # No energy_kwh supplied
    res = predict_expected_energy(payload)
    assert res["expected_energy_kwh"] >= 0.0
    assert "energy_kwh" not in res["features_used"]


def test_expected_energy_positivity_sanity():
    """Requirement 19: Verify expected energy prediction returns finite non-negative values."""
    for state in ["RUNNING", "IDLE", "SLEEP", "DEGRADED", "OVERLOAD"]:
        res = predict_expected_energy({"machine_id": "M01", "machine_state": state, "dt_seconds": 2.0})
        assert res["expected_energy_kwh"] >= 0.0
        assert np.isfinite(res["expected_energy_kwh"])


# ==============================================================================
# 5. ENERGY DEVIATION TESTS
# ==============================================================================

def test_energy_deviation_calculation():
    """Requirement 20: Verify energy deviation calculation."""
    # Actual 0.010 kWh vs Expected 0.008 kWh -> deviation = +0.002 kWh (+25%)
    res = calculate_energy_deviation(actual_energy_kwh=0.010, expected_energy_kwh=0.008)
    assert np.isclose(res["deviation_kwh"], 0.002, atol=1e-6)
    assert np.isclose(res["deviation_pct"], 25.0, atol=0.1)
    assert res["is_above_baseline"] is True

    # Test API endpoint POST /baseline/deviation
    resp = client.post("/baseline/deviation", json={"actual_energy_kwh": 0.010, "expected_energy_kwh": 0.008})
    assert resp.status_code == 200
    data = resp.json()
    assert np.isclose(data["deviation_kwh"], 0.002, atol=1e-6)
    assert np.isclose(data["deviation_pct"], 25.0, atol=0.1)
    assert data["is_above_baseline"] is True


def test_zero_expected_energy_handling():
    """Requirement 21: Verify safe handling when expected energy is zero (no division by zero)."""
    res = calculate_energy_deviation(actual_energy_kwh=0.005, expected_energy_kwh=0.0)
    assert res["deviation_kwh"] == 0.005
    assert np.isfinite(res["deviation_pct"])
    assert res["status"] == "OK"


def test_representative_state_predictions():
    """Requirement 22: Verify physical ordering of predictions: SLEEP < IDLE < RUNNING."""
    sleep_pred = predict_expected_energy({
        "machine_id": "M01",
        "machine_state": "SLEEP",
        "rpm": 0.0,
        "torque_nm": 0.0,
        "production_delta": 0,
        "dt_seconds": 2.0,
    })
    idle_pred = predict_expected_energy({
        "machine_id": "M01",
        "machine_state": "IDLE",
        "rpm": 20.0,
        "torque_nm": 0.0,
        "production_delta": 0,
        "dt_seconds": 2.0,
    })
    run_pred = predict_expected_energy({
        "machine_id": "M01",
        "machine_state": "RUNNING",
        "rpm": 1450.0,
        "torque_nm": 30.0,
        "production_delta": 1,
        "dt_seconds": 2.0,
    })

    assert sleep_pred["expected_energy_kwh"] < idle_pred["expected_energy_kwh"]
    assert idle_pred["expected_energy_kwh"] < run_pred["expected_energy_kwh"]



# ==============================================================================
# 6. CONSISTENCY & AUDIT TESTS
# ==============================================================================

def test_reproducibility():
    """Requirement 23: Verify reproducible metrics across identical random seeds."""
    meta1 = train_and_select_baseline(save_artifacts=False, random_state=42)
    meta2 = train_and_select_baseline(save_artifacts=False, random_state=42)
    assert meta1["selected_model"] == meta2["selected_model"]
    assert np.isclose(meta1["cv_metrics"]["cv_mae"], meta2["cv_metrics"]["cv_mae"], atol=1e-6)


def test_model_loading():
    """Requirement 24: Verify joblib can load V2 pipeline and predict."""
    loaded_pipe = joblib.load(V2_MODEL_PATH)
    assert hasattr(loaded_pipe, "predict")
    sample_df = pd.DataFrame([{
        "production_delta": 1.0,
        "production_rate": 60.0,
        "rpm": 1450.0,
        "torque_nm": 30.0,
        "temperature_c": 50.0,
        "vibration": 0.18,
        "health_score": 98.0,
        "anomaly_score": 0.01,
        "hour_of_day": 12.0,
        "day_of_week": 2.0,
        "dt_seconds": 2.0,
        "machine_state": "RUNNING",
        "machine_id": "M01",
    }])[ALL_FEATURE_COLUMNS]
    pred = loaded_pipe.predict(sample_df)
    assert len(pred) == 1
    assert pred[0] >= 0.0


def test_feature_order_consistency():
    """Requirement 25: Verify feature column order consistency."""
    service = EnergyBaselineService(model_path=str(V2_MODEL_PATH))
    assert service.pipeline is not None
    preprocessor = service.pipeline.named_steps["preprocessor"]
    # Check that preprocessor columns match NUMERIC_FEATURES + CATEGORICAL_FEATURES
    num_cols = preprocessor.transformers[0][2]
    cat_cols = preprocessor.transformers[1][2]
    assert num_cols == NUMERIC_FEATURES
    assert cat_cols == CATEGORICAL_FEATURES


def test_leakage_audit():
    """Requirement 26: Verify complete leakage audit in metadata passes all criteria."""
    with open(METADATA_PATH, "r") as f:
        meta = json.load(f)

    audit = meta["data_leakage_audit"]
    assert audit["no_power_kw_in_features"] is True
    assert audit["no_energy_kwh_in_features"] is True
    assert audit["no_current_a_in_features"] is True
    assert audit["no_voltage_v_in_features"] is True
    assert audit["target_is_interval_energy_kwh_only"] is True
    assert audit["no_random_train_test_split"] is True
    assert audit["no_random_kfold"] is True
    assert audit["chronological_validation_only"] is True
    assert audit["test_set_untouched_during_tuning"] is True
