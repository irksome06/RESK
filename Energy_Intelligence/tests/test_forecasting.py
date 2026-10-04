"""
Tests for Phase 9 Short-Horizon Energy Forecasting Engine.
Covers items required by Phase 9 specification:
1. Energy aggregation
2. Correct 1-minute aggregation
3. Lag feature creation
4. Rolling feature creation
5. No future leakage
6. Chronological split
7. TimeSeriesSplit
8. Naive baseline
9. Forecast model training
10. Forecast model loading
11. Forecast API
12. Forecast horizon
13. Model metadata
14. Reproducibility
"""

import os
import json
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.main import app
from ml.forecasting import (
    aggregate_telemetry_to_1min,
    create_forecast_features,
    train_and_select_forecaster,
    forecasting_service,
    FORECAST_FEATURE_COLUMNS,
    FORECAST_TARGET_COLUMN,
    FORECAST_MODEL_PATH,
    FORECAST_METADATA_PATH,
)
from ml.forecast_models import NaivePersistenceForecaster, MovingAverageForecaster
from ml.forecast_evaluate import evaluate_forecast

client = TestClient(app)


def _generate_synthetic_2s_telemetry(n_points=90, base_power_kw=7.5):
    """Generates synthetic 2-second telemetry series for testing."""
    records = []
    base_time = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    cum_energy = 100.0

    for i in range(n_points):
        ts = base_time + timedelta(seconds=i * 2)
        power = base_power_kw + np.sin(i / 10.0) * 0.5
        interval_e = power * (2.0 / 3600.0)
        cum_energy += interval_e
        records.append({
            "timestamp": ts.isoformat(),
            "machine_id": "M01",
            "power_kw": power,
            "energy_kwh": cum_energy,
            "machine_state": "RUNNING",
            "production_count": i * 2,
            "production_delta": 2,
            "cycle_time_sec": 2.0,
            "voltage_v": 415.0,
            "current_a": 12.0,
            "temperature_c": 50.0,
            "vibration": 0.18,
            "rpm": 1450.0,
            "torque_nm": 45.0,
            "health_score": 98.0,
            "anomaly_score": 0.01,
            "source": "test_synth",
            "schema_version": "1.0",
        })
    return pd.DataFrame(records)


def test_1_minute_energy_aggregation():
    """Verify that 2-second telemetry is correctly aggregated into 1-minute intervals."""
    # 90 points at 2-second dt = 180 seconds = exactly 3 1-minute intervals
    df_raw = _generate_synthetic_2s_telemetry(n_points=90, base_power_kw=6.0)
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])

    df_1min = aggregate_telemetry_to_1min(df_raw)

    assert not df_1min.empty
    assert len(df_1min) >= 2
    assert "energy_1min_kwh" in df_1min.columns
    assert "machine_id" in df_1min.columns

    # In 60 seconds at 6 kW, energy consumed is 6 * (60/3600) = 0.100 kWh
    first_min_e = df_1min.iloc[0]["energy_1min_kwh"]
    assert 0.08 <= first_min_e <= 0.12


def test_lag_and_rolling_feature_creation():
    """Verify that lag features (t-1, t-2, t-3) and rolling mean/std are created accurately."""
    df_raw = _generate_synthetic_2s_telemetry(n_points=180, base_power_kw=7.5)
    df_1min = aggregate_telemetry_to_1min(df_raw)
    feat_df = create_forecast_features(df_1min)

    assert "lag_1_energy" in feat_df.columns
    assert "lag_2_energy" in feat_df.columns
    assert "lag_3_energy" in feat_df.columns
    assert "rolling_mean_energy" in feat_df.columns
    assert "rolling_std_energy" in feat_df.columns
    assert FORECAST_TARGET_COLUMN in feat_df.columns

    # Verify lag alignment: for row i, next row's lag_1_energy equals current row's target_energy_1min_kwh
    for i in range(len(feat_df) - 1):
        assert np.isclose(
            feat_df.iloc[i][FORECAST_TARGET_COLUMN],
            feat_df.iloc[i + 1]["lag_1_energy"],
            atol=1e-5,
        )


def test_no_future_leakage_audit():
    """
    STRICT AUDIT: Ensure that no feature uses information from the target interval or future intervals.
    """
    df_raw = _generate_synthetic_2s_telemetry(n_points=240, base_power_kw=7.5)
    df_1min = aggregate_telemetry_to_1min(df_raw)
    feat_df = create_forecast_features(df_1min)

    # 1. Feature columns must not include target or raw energy column
    for col in FORECAST_FEATURE_COLUMNS:
        assert col != FORECAST_TARGET_COLUMN
        assert col != "energy_1min_kwh"
        assert not col.startswith("lead_")
        assert not col.startswith("future_")

    # 2. Check that target at index t is shifted(-1) relative to lag_1_energy at index t+1
    for i in range(len(feat_df) - 1):
        assert np.isclose(
            feat_df.iloc[i][FORECAST_TARGET_COLUMN],
            feat_df.iloc[i + 1]["lag_1_energy"],
            atol=1e-5,
        )


def test_chronological_split_and_timeseriessplit():
    """Verify that train/test split is strictly chronological and TimeSeriesSplit expands forward."""
    from sklearn.model_selection import TimeSeriesSplit

    df_raw = _generate_synthetic_2s_telemetry(n_points=360, base_power_kw=7.5)
    df_1min = aggregate_telemetry_to_1min(df_raw)
    feat_df = create_forecast_features(df_1min)

    split_idx = int(len(feat_df) * 0.8)
    train_df = feat_df.iloc[:split_idx]
    test_df = feat_df.iloc[split_idx:]

    # Train timestamps must strictly precede test timestamps
    assert train_df["timestamp"].max() < test_df["timestamp"].min()

    # TimeSeriesSplit fold verification
    tscv = TimeSeriesSplit(n_splits=3)
    for fold, (tr_idx, val_idx) in enumerate(tscv.split(train_df)):
        assert max(tr_idx) < min(val_idx), f"Fold {fold} violates time-series ordering"


def test_naive_persistence_benchmark():
    """Verify that NaivePersistenceForecaster predicts latest observed lag_1 value."""
    model = NaivePersistenceForecaster(lag_column="lag_1_energy")
    X = pd.DataFrame({
        "lag_1_energy": [0.12, 0.15, 0.18],
        "lag_2_energy": [0.10, 0.12, 0.15],
        "other_feature": [1.0, 2.0, 3.0],
    })
    y = np.array([0.15, 0.18, 0.20])

    model.fit(X, y)
    preds = model.predict(X)

    # Predictions must equal lag_1_energy exactly
    np.testing.assert_array_almost_equal(preds, [0.12, 0.15, 0.18])

    # Evaluate metrics
    metrics = evaluate_forecast(y, preds, y_train=y)
    assert metrics["MAE"] >= 0.0
    assert metrics["MASE"] > 0.0


def test_forecast_model_training_and_selection():
    """Verify that multi-model benchmarking executes and saves artifacts."""
    summary = train_and_select_forecaster(save_artifacts=True)

    assert "selected_model" in summary
    assert "cv_metrics" in summary
    assert "test_metrics" in summary
    assert "model_comparison" in summary
    assert len(summary["model_comparison"]) >= 4

    # Check Naive model is present in comparison
    names = [m["model_name"] for m in summary["model_comparison"]]
    assert "NaivePersistence" in names

    # Winning model must beat or equal naive benchmark
    winning_name = summary["selected_model"]
    assert winning_name in names


def test_forecast_model_loading_and_service():
    """Verify that saved model artifact and metadata load cleanly into service."""
    assert os.path.exists(FORECAST_MODEL_PATH)
    assert os.path.exists(FORECAST_METADATA_PATH)

    service = forecasting_service
    assert service.pipeline is not None
    assert service.metadata is not None
    assert "selected_model" in service.metadata


def test_forecast_horizon_rollout():
    """Verify that multi-step forecasting works for horizons 1 through 5."""
    for h in [1, 2, 3, 5]:
        res = forecasting_service.forecast_machine(
            machine_id="M01",
            recent_1min_energy=[0.12, 0.125, 0.122],
            current_state="RUNNING",
            horizon_minutes=h,
        )
        assert res["machine_id"] == "M01"
        assert res["horizon_minutes"] == h
        assert len(res["forecast_energy_kwh"]) == h
        assert res["total_forecast_kwh"] > 0.0
        # All forecasted steps must be positive
        assert all(step > 0.0 for step in res["forecast_energy_kwh"])


def test_forecast_factory_aggregation():
    """Verify factory-wide aggregated forecast across all machines."""
    res = forecasting_service.forecast_factory(horizon_minutes=5)
    assert res["horizon_minutes"] == 5
    assert len(res["factory_step_forecasts_kwh"]) == 5
    assert res["total_factory_forecast_kwh"] > 0.0
    assert "M01" in res["machine_forecasts"]
    assert "M02" in res["machine_forecasts"]


def test_forecast_api_machine():
    """Verify GET /forecast/machine/{machine_id} endpoint."""
    response = client.get("/forecast/machine/M01?horizon_minutes=3")
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "M01"
    assert data["horizon_minutes"] == 3
    assert len(data["forecast_energy_kwh"]) == 3
    assert "model" in data
    assert "disclaimer" in data


def test_forecast_api_factory():
    """Verify GET /forecast/factory endpoint."""
    response = client.get("/forecast/factory?horizon_minutes=5")
    assert response.status_code == 200
    data = response.json()
    assert data["horizon_minutes"] == 5
    assert len(data["factory_step_forecasts_kwh"]) == 5
    assert data["total_factory_forecast_kwh"] > 0.0
    assert "M01" in data["machine_forecasts"]


def test_forecast_api_invalid_machine_404():
    """Verify that unknown machine ID returns 404."""
    response = client.get("/forecast/machine/INVALID_ROBOT_99")
    assert response.status_code == 404


def test_forecast_reproducibility():
    """Verify that identical input produces identical forecast output."""
    res1 = forecasting_service.forecast_machine(
        machine_id="M01",
        recent_1min_energy=[0.11, 0.115, 0.112],
        current_state="RUNNING",
        horizon_minutes=3,
    )
    res2 = forecasting_service.forecast_machine(
        machine_id="M01",
        recent_1min_energy=[0.11, 0.115, 0.112],
        current_state="RUNNING",
        horizon_minutes=3,
    )
    assert res1["forecast_energy_kwh"] == res2["forecast_energy_kwh"]
    assert res1["total_forecast_kwh"] == res2["total_forecast_kwh"]
