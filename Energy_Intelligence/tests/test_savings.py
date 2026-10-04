"""
Phase 10 Savings Estimation, Efficiency Analytics & Optimization Intelligence Tests.
Covers all 26 required items:
1. Potential savings calculation
2. Negative savings clamping
3. Persistent savings
4. Savings percentage
5. Cost calculation
6. CO2 calculation
7. Configurable tariff
8. Configurable emission factor
9. SEC calculation
10. Zero production handling
11. Machine-level efficiency
12. State-level efficiency
13. Before/after comparison
14. Production-normalized comparison
15. Savings verification
16. Verification statuses (NO_BASELINE, INSUFFICIENT_DATA, NO_IMPROVEMENT, IMPROVEMENT_DETECTED, SAVINGS_VERIFIED)
17. ROI
18. Payback
19. Zero monthly savings
20. Missing implementation cost
21. Opportunity detection
22. Opportunity priority
23. API schemas
24. API endpoints
25. Phase 8.1 regression test
26. Phase 9 regression test
27. Reconciliation checks (no double counting)
"""

import pytest
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.main import app
from database.schemas import TelemetryRecord, MachineState
from analytics.savings import (
    calculate_potential_savings,
    calculate_roi_payback,
    verify_savings,
    compute_machine_savings,
)
from analytics.efficiency import (
    calculate_sec,
    compute_machine_efficiency,
    compute_factory_efficiency,
    compute_state_efficiency,
)
from analytics.optimization import opportunity_engine

client = TestClient(app)


def _make_telemetry_series(
    machine_id: str = "M01",
    n_points: int = 20,
    power_kw: float = 7.5,
    state: MachineState = MachineState.RUNNING,
    prod_per_interval: int = 2,
    base_energy: float = 100.0,
    start_time: Optional[datetime] = None,
) -> list[TelemetryRecord]:
    records = []
    base_time = start_time or datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    cum_e = base_energy
    cum_prod = 0

    for i in range(n_points):
        ts = base_time + timedelta(seconds=i * 2)
        interval_e = power_kw * (2.0 / 3600.0)
        cum_e += interval_e
        cum_prod += prod_per_interval
        records.append(
            TelemetryRecord(
                timestamp=ts,
                machine_id=machine_id,
                power_kw=power_kw,
                energy_kwh=round(cum_e, 6),
                machine_state=state,
                production_count=cum_prod,
                production_delta=prod_per_interval,
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
            )
        )
    return records


# ==========================================
# 1-8: SAVINGS & ECONOMIC METRICS
# ==========================================

def test_potential_savings_calculation():
    """Verify potential savings: max(0, actual - expected)."""
    res = calculate_potential_savings(actual_energy_kwh=10.0, expected_energy_kwh=8.0)
    assert res["deviation_kwh"] == 2.0
    assert res["potential_savings_kwh"] == 2.0
    assert res["savings_rate_pct"] == 20.0
    assert res["baseline_gap_pct"] == 25.0


def test_negative_savings_clamping():
    """Verify that when actual < expected, potential savings is clamped to 0.0 (no negative savings)."""
    res = calculate_potential_savings(actual_energy_kwh=6.0, expected_energy_kwh=8.0)
    assert res["deviation_kwh"] == -2.0
    assert res["potential_savings_kwh"] == 0.0
    assert res["potential_savings_inr"] == 0.0
    assert res["potential_co2_savings_kg"] == 0.0
    assert res["savings_rate_pct"] == 0.0


def test_persistent_savings_separation():
    """Verify persistent opportunity is only recorded when interval is persistent."""
    res_non_pers = calculate_potential_savings(actual_energy_kwh=10.0, expected_energy_kwh=8.0, is_persistent=False)
    assert res_non_pers["potential_savings_kwh"] == 2.0
    assert res_non_pers["persistent_opportunity_kwh"] == 0.0

    res_pers = calculate_potential_savings(actual_energy_kwh=10.0, expected_energy_kwh=8.0, is_persistent=True)
    assert res_pers["potential_savings_kwh"] == 2.0
    assert res_pers["persistent_opportunity_kwh"] == 2.0


def test_cost_and_co2_calculation_configurable():
    """Verify cost and CO2 calculations with configurable tariff and emission factor."""
    res = calculate_potential_savings(
        actual_energy_kwh=10.0,
        expected_energy_kwh=5.0,
        tariff_inr=10.0,
        emission_factor_kg=0.80,
    )
    assert res["potential_savings_kwh"] == 5.0
    assert res["potential_savings_inr"] == 50.0  # 5 * 10
    assert res["potential_co2_savings_kg"] == 4.0  # 5 * 0.8


# ==========================================
# 9-12: SEC & EFFICIENCY
# ==========================================

def test_sec_calculation():
    """Verify SEC = energy_kwh / production_units."""
    sec = calculate_sec(energy_kwh=100.0, production_units=500.0)
    assert sec == 0.20


def test_zero_production_handling():
    """Verify that zero or missing production returns None (never 0, never div by zero)."""
    assert calculate_sec(energy_kwh=100.0, production_units=0) is None
    assert calculate_sec(energy_kwh=100.0, production_units=None) is None
    assert calculate_sec(energy_kwh=None, production_units=50) is None


def test_machine_level_efficiency():
    """Verify machine-level efficiency aggregation."""
    recs = _make_telemetry_series(machine_id="M01", n_points=20, power_kw=7.5, prod_per_interval=2)
    m_eff = compute_machine_efficiency(recs)
    assert m_eff["machine_id"] == "M01"
    assert m_eff["production_units"] > 0
    assert m_eff["actual_sec_kwh_per_unit"] is not None
    assert m_eff["actual_energy_kwh"] > 0.0


def test_state_level_efficiency():
    """Verify state-level breakdown across operating states."""
    recs = _make_telemetry_series(machine_id="M01", n_points=10, power_kw=7.5, state=MachineState.RUNNING, base_energy=100.0)
    last_e = recs[-1].energy_kwh
    last_ts = recs[-1].timestamp + timedelta(seconds=2)
    recs += _make_telemetry_series(machine_id="M01", n_points=10, power_kw=1.5, state=MachineState.IDLE, base_energy=last_e, start_time=last_ts)
    s_eff = compute_state_efficiency(recs)
    assert "RUNNING" in s_eff
    assert "IDLE" in s_eff
    assert s_eff["RUNNING"]["actual_energy_kwh"] > 0.0
    assert s_eff["IDLE"]["actual_energy_kwh"] > 0.0


# ==========================================
# 13-16: SAVINGS VERIFICATION & STATUSES
# ==========================================

def test_savings_verification_statuses():
    """Verify all 5 verification statuses."""
    # 1. NO_BASELINE: zero baseline energy or production
    v1 = verify_savings(baseline_actual_energy_kwh=0.0, baseline_production_units=0.0, post_actual_energy_kwh=50.0, post_production_units=500.0)
    assert v1["status"] == "NO_BASELINE"

    # 2. INSUFFICIENT_DATA: intervals below threshold
    v2 = verify_savings(baseline_actual_energy_kwh=100.0, baseline_production_units=500.0, post_actual_energy_kwh=80.0, post_production_units=500.0, baseline_intervals=2, post_intervals=2, min_intervals=5)
    assert v2["status"] == "INSUFFICIENT_DATA"

    # 3. NO_IMPROVEMENT: post SEC is higher or equal to baseline SEC
    # baseline SEC = 100 / 500 = 0.20, post SEC = 110 / 500 = 0.22
    v3 = verify_savings(baseline_actual_energy_kwh=100.0, baseline_production_units=500.0, post_actual_energy_kwh=110.0, post_production_units=500.0)
    assert v3["status"] == "NO_IMPROVEMENT"
    assert v3["normalized_savings_kwh"] == 0.0

    # 4. IMPROVEMENT_DETECTED: positive improvement but below significance threshold (e.g. 1% vs 2% threshold)
    # baseline SEC = 100 / 500 = 0.20, post SEC = 99 / 500 = 0.198 (1.0% improvement)
    v4 = verify_savings(baseline_actual_energy_kwh=100.0, baseline_production_units=500.0, post_actual_energy_kwh=99.0, post_production_units=500.0, significance_threshold_pct=2.0)
    assert v4["status"] == "IMPROVEMENT_DETECTED"
    assert v4["normalized_savings_kwh"] == 1.0

    # 5. SAVINGS_VERIFIED: significant improvement >= significance_threshold_pct
    # baseline SEC = 100 / 500 = 0.20, post SEC = 85 / 500 = 0.170 (15.0% improvement)
    v5 = verify_savings(baseline_actual_energy_kwh=100.0, baseline_production_units=500.0, post_actual_energy_kwh=85.0, post_production_units=500.0, significance_threshold_pct=2.0)
    assert v5["status"] == "SAVINGS_VERIFIED"
    assert v5["normalized_savings_kwh"] == 15.0
    assert v5["sec_improvement_pct"] == 15.0


def test_production_normalized_vs_raw_energy_trap():
    """
    TRAP TEST: Raw energy decreased, but SEC worsened!
    Before: 1000 kWh, 1000 units (SEC = 1.0)
    After: 900 kWh, 800 units (SEC = 1.125)
    Raw energy decreased by 100 kWh, but efficiency worsened!
    Verification must correctly flag NO_IMPROVEMENT.
    """
    v = verify_savings(
        baseline_actual_energy_kwh=1000.0,
        baseline_production_units=1000.0,
        post_actual_energy_kwh=900.0,
        post_production_units=800.0,
    )
    assert v["status"] == "NO_IMPROVEMENT"
    assert v["sec_improvement_pct"] < 0.0
    assert v["normalized_savings_kwh"] == 0.0


# ==========================================
# 17-20: ROI & FINANCIAL PAYBACK
# ==========================================

def test_roi_and_payback():
    """Verify annual savings and payback horizon."""
    # Monthly savings = 10,000 INR, Cost = 50,000 INR -> Payback = 5.0 months
    roi = calculate_roi_payback(monthly_savings_inr=10000.0, implementation_cost_inr=50000.0)
    assert roi["annual_savings_inr"] == 120000.0
    assert roi["payback_months"] == 5.0

    # Zero monthly savings -> Payback is None
    roi_zero = calculate_roi_payback(monthly_savings_inr=0.0, implementation_cost_inr=50000.0)
    assert roi_zero["payback_months"] is None

    # Missing implementation cost -> Payback is None
    roi_no_cost = calculate_roi_payback(monthly_savings_inr=10000.0, implementation_cost_inr=None)
    assert roi_no_cost["payback_months"] is None


# ==========================================
# 21-22: OPTIMIZATION OPPORTUNITY ENGINE
# ==========================================

def test_optimization_opportunity_engine_detection():
    """Verify opportunity engine identifies conditions (idle energy, degraded state)."""
    # Create idle heavy series
    recs = _make_telemetry_series("M01", n_points=5, power_kw=7.5, state=MachineState.RUNNING)
    recs += _make_telemetry_series("M01", n_points=25, power_kw=2.0, state=MachineState.IDLE)
    opps = opportunity_engine.evaluate_machine("M01", recs)

    assert any(o["category"] == "IDLE_REDUCTION" for o in opps)
    # Check priority levels and scores
    for o in opps:
        assert 0.0 <= o["priority_score"] <= 100.0
        assert o["priority_level"] in ["HIGH", "MEDIUM", "LOW"]
        assert "suggested_action" in o
        assert "supporting_metric" in o


# ==========================================
# 24: REST API ENDPOINTS
# ==========================================

def test_api_savings_factory():
    """Verify GET /savings/factory."""
    response = client.get("/savings/factory?recent_intervals=20")
    assert response.status_code == 200
    data = response.json()
    assert "actual_energy_kwh" in data
    assert "expected_energy_kwh" in data
    assert "potential_savings_kwh" in data
    assert "potential_savings_inr" in data
    assert "tariff_inr_per_kwh" in data


def test_api_savings_machine():
    """Verify GET /savings/machine/{machine_id}."""
    response = client.get("/savings/machine/M01?recent_intervals=20")
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "M01"
    assert "potential_savings_kwh" in data
    assert "potential_savings_inr" in data
    assert "deviation_status" in data


def test_api_savings_states():
    """Verify GET /savings/states."""
    response = client.get("/savings/states?recent_intervals=30")
    assert response.status_code == 200
    data = response.json()
    assert "total_actual_kwh" in data
    assert "total_expected_kwh" in data
    assert "states" in data
    assert len(data["states"]) > 0


def test_api_efficiency_factory():
    """Verify GET /efficiency/factory."""
    response = client.get("/efficiency/factory?recent_intervals=20")
    assert response.status_code == 200
    data = response.json()
    assert "production_units" in data
    assert "actual_energy_kwh" in data
    assert "actual_sec_kwh_per_unit" in data
    assert "machine_count" in data


def test_api_efficiency_machine():
    """Verify GET /efficiency/machine/{machine_id}."""
    response = client.get("/efficiency/machine/M01?recent_intervals=20")
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "M01"
    assert "actual_sec_kwh_per_unit" in data


def test_api_savings_verify():
    """Verify POST /savings/verify."""
    payload = {
        "intervention_id": "INT-M01-01",
        "machine_id": "M01",
        "intervention_type": "IDLE_REDUCTION",
        "baseline_actual_energy_kwh": 100.0,
        "baseline_production_units": 500.0,
        "post_actual_energy_kwh": 85.0,
        "post_production_units": 500.0,
        "baseline_intervals": 20,
        "post_intervals": 20,
        "implementation_cost_inr": 5000.0,
    }
    response = client.post("/savings/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SAVINGS_VERIFIED"
    assert data["normalized_savings_kwh"] == 15.0
    assert data["sec_improvement_pct"] == 15.0
    assert data["payback_months"] is not None


def test_api_optimization_opportunities():
    """Verify GET /optimization/opportunities."""
    response = client.get("/optimization/opportunities?recent_intervals=30")
    assert response.status_code == 200
    data = response.json()
    assert "total_opportunities" in data
    assert "high_priority_count" in data
    assert "opportunities" in data


def test_legacy_machine_savings_endpoint():
    """Verify backward compatibility of GET /machines/{machine_id}/savings."""
    response = client.get("/machines/M01/savings")
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "M01"
    assert "energy_saved_kwh" in data
    assert "cost_saved_inr" in data
    assert "co2_avoided_kg" in data


# ==========================================
# 25-26: REGRESSION TESTS
# ==========================================

def test_phase_8_1_baseline_regression():
    """Ensure Phase 8.1 production-aware baseline continues to work."""
    payload = {
        "machine_id": "M01",
        "machine_state": "RUNNING",
        "production_delta": 2,
        "dt_seconds": 2.0,
        "rpm": 1450.0,
        "torque_nm": 45.0,
        "temperature_c": 50.0,
    }
    response = client.post("/baseline/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["expected_energy_kwh"] > 0.0


def test_phase_9_forecasting_regression():
    """Ensure Phase 9 forecast and deviation endpoints continue to work."""
    f_res = client.get("/forecast/factory?horizon_minutes=3")
    assert f_res.status_code == 200
    assert len(f_res.json()["factory_step_forecasts_kwh"]) == 3

    d_res = client.get("/deviation/factory?recent_intervals=20")
    assert d_res.status_code == 200
    assert "factory_deviation_kwh" in d_res.json()


# ==========================================
# 27: RECONCILIATION & NO DOUBLE COUNTING
# ==========================================

def test_reconciliation_machine_to_factory():
    """
    RECONCILIATION TEST:
    Verify sum(machine_actual_energy) == factory_actual_energy
    and sum(machine_expected_energy) == factory_expected_energy
    within floating-point tolerance.
    """
    m1_recs = _make_telemetry_series("M01", n_points=10, power_kw=5.0)
    m2_recs = _make_telemetry_series("M02", n_points=10, power_kw=8.0)

    m1_eff = compute_machine_efficiency(m1_recs)
    m2_eff = compute_machine_efficiency(m2_recs)

    m_dict = {"M01": m1_recs, "M02": m2_recs}
    factory_eff = compute_factory_efficiency(m_dict)

    machine_sum_act = m1_eff["actual_energy_kwh"] + m2_eff["actual_energy_kwh"]
    machine_sum_exp = m1_eff["expected_energy_kwh"] + m2_eff["expected_energy_kwh"]

    assert np.isclose(machine_sum_act, factory_eff["actual_energy_kwh"], atol=1e-5)
    assert np.isclose(machine_sum_exp, factory_eff["expected_energy_kwh"], atol=1e-5)
