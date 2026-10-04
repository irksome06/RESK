"""
Tests for Phase 9 Energy Deviation & Intelligence Engine.
Covers items required by Phase 9 specification:
1. Deviation calculation (actual, expected, deviation_kwh, deviation_pct)
2. Zero expected energy handling
3. Persistent deviation detection (threshold, consecutive intervals, statuses)
4. Machine contribution calculation
5. Zero total-positive-deviation handling
6. State-level aggregation
7. Factory-level aggregation
8. Deviation REST endpoints (/deviation/machine/{id}, /deviation/factory, /deviation/contributors, /deviation/states)
9. Regression verification: Phase 8.1 baseline model still functions
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.main import app
from database.schemas import TelemetryRecord, MachineState
from analytics.deviation import (
    calculate_energy_deviation,
    compute_machine_deviation_from_records,
    analyze_state_deviations,
)
from analytics.persistence import PersistentDeviationDetector
from analytics.contribution import compute_machine_contributions

client = TestClient(app)


def _make_sample_record(
    machine_id: str,
    ts: datetime,
    energy_kwh: float,
    power_kw: float = 7.5,
    state: MachineState = MachineState.RUNNING,
    prod_delta: int = 1,
) -> TelemetryRecord:
    return TelemetryRecord(
        timestamp=ts,
        machine_id=machine_id,
        power_kw=power_kw,
        energy_kwh=energy_kwh,
        machine_state=state,
        production_count=100,
        production_delta=prod_delta,
        cycle_time_sec=2.0,
        voltage_v=415.0,
        current_a=12.0,
        temperature_c=50.0,
        vibration=0.18,
        rpm=1450.0,
        torque_nm=45.0,
        health_score=98.0,
        anomaly_score=0.01,
        source="simulator",
        schema_version="1.0",
    )


def test_calculate_energy_deviation_basic():
    """Verify standard deviation calculation."""
    # Actual > Expected (Above baseline)
    res = calculate_energy_deviation(actual_energy_kwh=0.150, expected_energy_kwh=0.100)
    assert abs(res["deviation_kwh"] - 0.050) < 1e-5
    assert abs(res["deviation_pct"] - 50.0) < 1e-2
    assert res["is_above_baseline"] is True
    assert res["status"] == "ABOVE_BASELINE"

    # Actual < Expected (Below baseline)
    res2 = calculate_energy_deviation(actual_energy_kwh=0.080, expected_energy_kwh=0.100)
    assert abs(res2["deviation_kwh"] - (-0.020)) < 1e-5
    assert abs(res2["deviation_pct"] - (-20.0)) < 1e-2
    assert res2["is_above_baseline"] is False
    assert res2["status"] == "BELOW_BASELINE"

    # Actual ~ Expected (Normal)
    res3 = calculate_energy_deviation(actual_energy_kwh=0.102, expected_energy_kwh=0.100)
    assert abs(res3["deviation_pct"] - 2.0) < 1e-2
    assert res3["status"] == "NORMAL"


def test_zero_expected_energy_handling():
    """Verify safe division when expected energy is zero or near zero."""
    res = calculate_energy_deviation(actual_energy_kwh=0.05, expected_energy_kwh=0.0)
    assert res["deviation_kwh"] == 0.05
    assert res["deviation_pct"] == 100.0  # safe capped fallback
    assert res["status"] == "ABOVE_BASELINE"

    res_zero = calculate_energy_deviation(actual_energy_kwh=0.0, expected_energy_kwh=0.0)
    assert res_zero["deviation_kwh"] == 0.0
    assert res_zero["deviation_pct"] == 0.0
    assert res_zero["status"] == "NORMAL"


def test_persistent_deviation_detector_logic():
    """
    Verify persistence detector:
    - Single spike does NOT trigger persistent alert
    - N consecutive above-threshold intervals DO trigger PERSISTENT_ABOVE_BASELINE
    """
    detector = PersistentDeviationDetector(threshold_pct=15.0, consecutive_intervals=3)

    # 1. Single transient spike
    intervals_spike = [
        {"deviation_pct": 2.0},
        {"deviation_pct": 25.0},  # single spike
        {"deviation_pct": 1.0},
    ]
    eval1 = detector.evaluate_intervals(intervals_spike)
    assert eval1["overall_status"] == "NORMAL"
    assert eval1["is_persistent"] is False
    assert eval1["max_consecutive_above"] == 1

    # 2. Exactly 2 consecutive above-threshold intervals (below threshold of 3)
    intervals_two = [
        {"deviation_pct": 1.0},
        {"deviation_pct": 18.0},
        {"deviation_pct": 20.0},
    ]
    eval2 = detector.evaluate_intervals(intervals_two)
    assert eval2["overall_status"] == "ABOVE_BASELINE"
    assert eval2["is_persistent"] is False
    assert eval2["current_consecutive_above"] == 2

    # 3. 3 consecutive above-threshold intervals -> PERSISTENT_ABOVE_BASELINE
    intervals_persistent = [
        {"deviation_pct": 2.0},
        {"deviation_pct": 22.0},
        {"deviation_pct": 24.0},
        {"deviation_pct": 20.0},
    ]
    eval3 = detector.evaluate_intervals(intervals_persistent)
    assert eval3["overall_status"] == "PERSISTENT_ABOVE_BASELINE"
    assert eval3["is_persistent"] is True
    assert eval3["current_consecutive_above"] == 3


def test_machine_contribution_calculation():
    """Verify machine ranking and contribution percentages to positive factory deviation."""
    deviations = [
        {"machine_id": "M01", "actual_energy_kwh": 10.0, "expected_energy_kwh": 8.0, "deviation_kwh": 2.0, "deviation_pct": 25.0},
        {"machine_id": "M02", "actual_energy_kwh": 15.0, "expected_energy_kwh": 9.0, "deviation_kwh": 6.0, "deviation_pct": 66.7},
        {"machine_id": "M03", "actual_energy_kwh": 5.0, "expected_energy_kwh": 5.0, "deviation_kwh": 0.0, "deviation_pct": 0.0},
        {"machine_id": "M04", "actual_energy_kwh": 4.0, "expected_energy_kwh": 6.0, "deviation_kwh": -2.0, "deviation_pct": -33.3},
    ]

    res = compute_machine_contributions(deviations)

    # Total positive deviation = M01 (2.0) + M02 (6.0) = 8.0 kWh
    assert abs(res["total_positive_deviation_kwh"] - 8.0) < 1e-4

    contributors = res["contributors"]
    # Ranked descending: M02 first, M01 second
    assert contributors[0]["machine_id"] == "M02"
    assert abs(contributors[0]["contribution_pct"] - 75.0) < 1e-2  # 6.0 / 8.0 * 100

    assert contributors[1]["machine_id"] == "M01"
    assert abs(contributors[1]["contribution_pct"] - 25.0) < 1e-2  # 2.0 / 8.0 * 100

    # Negative deviator M04 has 0% contribution to positive deviation
    assert contributors[3]["machine_id"] == "M04"
    assert contributors[3]["contribution_pct"] == 0.0


def test_zero_total_positive_deviation_handling():
    """Verify safe zero division handling when all machines are below or at baseline."""
    deviations = [
        {"machine_id": "M01", "actual_energy_kwh": 4.0, "expected_energy_kwh": 5.0, "deviation_kwh": -1.0, "deviation_pct": -20.0},
        {"machine_id": "M02", "actual_energy_kwh": 6.0, "expected_energy_kwh": 6.0, "deviation_kwh": 0.0, "deviation_pct": 0.0},
    ]

    res = compute_machine_contributions(deviations)
    assert res["total_positive_deviation_kwh"] == 0.0
    for c in res["contributors"]:
        assert c["contribution_pct"] == 0.0


def test_state_level_aggregation():
    """Verify that records are partitioned and aggregated by operational state."""
    base_t = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    records = [
        _make_sample_record("M01", base_t, 100.00, power_kw=7.5, state=MachineState.RUNNING),
        _make_sample_record("M01", base_t + timedelta(seconds=2), 100.005, power_kw=7.5, state=MachineState.RUNNING),
        _make_sample_record("M01", base_t + timedelta(seconds=4), 100.007, power_kw=1.5, state=MachineState.IDLE),
        _make_sample_record("M01", base_t + timedelta(seconds=6), 100.008, power_kw=1.5, state=MachineState.IDLE),
    ]

    state_breakdown = analyze_state_deviations(records)

    assert "RUNNING" in state_breakdown
    assert "IDLE" in state_breakdown
    assert state_breakdown["RUNNING"]["sample_count"] >= 1
    assert state_breakdown["IDLE"]["sample_count"] >= 1


def test_deviation_api_machine():
    """Verify GET /deviation/machine/{machine_id}."""
    response = client.get("/deviation/machine/M01?recent_intervals=20")
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "M01"
    assert "actual_energy_kwh" in data
    assert "expected_energy_kwh" in data
    assert "deviation_kwh" in data
    assert "status" in data
    assert "persistent_intervals" in data


def test_deviation_api_factory():
    """Verify GET /deviation/factory."""
    response = client.get("/deviation/factory?recent_intervals=20")
    assert response.status_code == 200
    data = response.json()
    assert "factory_actual_energy_kwh" in data
    assert "factory_expected_energy_kwh" in data
    assert "factory_deviation_kwh" in data
    assert "machine_count" in data


def test_deviation_api_contributors():
    """Verify GET /deviation/contributors."""
    response = client.get("/deviation/contributors?recent_intervals=20")
    assert response.status_code == 200
    data = response.json()
    assert "factory_deviation_kwh" in data
    assert "total_positive_factory_deviation" in data
    assert "contributors" in data
    assert len(data["contributors"]) > 0
    # Check contributor keys
    c = data["contributors"][0]
    assert "machine_id" in c
    assert "contribution_pct" in c
    assert "deviation_kwh" in c


def test_deviation_api_states():
    """Verify GET /deviation/states."""
    response = client.get("/deviation/states?recent_intervals=30")
    assert response.status_code == 200
    data = response.json()
    assert "total_actual_kwh" in data
    assert "total_expected_kwh" in data
    assert "total_deviation_kwh" in data
    assert "states" in data
    assert len(data["states"]) > 0


def test_phase_8_1_baseline_regression():
    """
    REGRESSION AUDIT: Verify that Phase 8.1 expected energy baseline endpoint
    continues to work without electrical target proxy features.
    """
    payload = {
        "machine_id": "M01",
        "machine_state": "RUNNING",
        "production_delta": 2,
        "dt_seconds": 2.0,
        "rpm": 1450.0,
        "torque_nm": 48.0,
        "temperature_c": 52.0,
        "vibration": 0.18,
        "health_score": 97.0,
        "anomaly_score": 0.02,
        "hour_of_day": 10.0,
        "day_of_week": 2.0,
    }
    response = client.post("/baseline/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "expected_energy_kwh" in data
    assert data["expected_energy_kwh"] > 0.0
    assert data["model_version"] == "v2_production_aware"
