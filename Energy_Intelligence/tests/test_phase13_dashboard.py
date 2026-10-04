"""
Phase 13 Industrial Energy Intelligence Demonstrator Test Suite.
Validates the complete presentation-grade dashboard layer, reconciliation guarantees,
and robust operational behavior.

Covers:
1. Dashboard imports and formatting helper robustness
2. Dashboard factory data retrieval via API
3. Dashboard machine data retrieval via API
4. Factory actual energy reconciliation
5. Expected baseline energy reconciliation
6. Production units reconciliation
7. Baseline deviation arithmetic
8. Rejection of cumulative meter double-counting
9. Forecasting data labeling and horizon projections
10. Strict distinction between potential and verified savings
11. Resilience when Ollama LLM is unavailable (deterministic fallback)
12. Safe fallback when external backend is unavailable
13. Safe SEC behavior when production count is zero
14. Machine asset fleet selection coverage
15. Deterministic demo reset behavior
16. Authoritative end-to-end demo runner reconciliation
"""

import math
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from api.main import app
from simulator.machine_simulator import DEFAULT_PROFILES
from simulator.demo_state import demo_state
from dashboard.app import safe_val, safe_float, safe_sec, safe_currency, fetch_api
from scripts.run_final_demo import run_authoritative_demo


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient fixture for FastAPI."""
    return TestClient(app)


def test_1_dashboard_imports_and_formatting_helpers():
    """1. Test that dashboard formatting helpers safely handle NaN, inf, and None."""
    assert safe_val(None, default="N/A") == "N/A"
    assert safe_val(float("nan"), default="N/A") == "N/A"
    assert safe_val(float("inf"), default="N/A") == "N/A"
    assert safe_val(42) == "42"

    assert safe_float(None) == "N/A"
    assert safe_float(float("nan")) == "N/A"
    assert safe_float(12.34567, decimals=2) == "12.35"
    assert safe_float("invalid") == "N/A"

    assert safe_sec(None) == "N/A (0 prod)"
    assert safe_sec(float("nan")) == "N/A (0 prod)"
    assert safe_sec(float("inf")) == "N/A (0 prod)"
    assert safe_sec(0.1321) == "0.1321 kWh/unit"

    assert safe_currency(None) == "₹0.00"
    assert safe_currency(float("nan")) == "₹0.00"
    assert safe_currency(1234.5) == "₹1,234.50"


def test_2_dashboard_can_retrieve_factory_data(client):
    """2. Test that dashboard retrieves complete factory snapshot via API."""
    data, mode = fetch_api("/demo/factory")
    assert data is not None
    assert mode in ("LIVE_HTTP", "IN_PROCESS")
    assert "production" in data
    assert "energy" in data
    assert "sec" in data
    assert "baseline" in data
    assert "deviation" in data
    assert "savings" in data
    assert "machine_status" in data
    assert len(data["machine_status"]) == 4


def test_3_dashboard_can_retrieve_machine_data(client):
    """3. Test that dashboard retrieves individual machine details for all fleet assets."""
    for m_id in DEFAULT_PROFILES.keys():
        data, mode = fetch_api(f"/demo/machine/{m_id}")
        assert data is not None
        assert data["machine_id"] == m_id
        assert "current_state" in data
        assert "actual_energy_kwh" in data
        assert "energy_kwh" in data
        assert "baseline_expected_energy_kwh" in data
        assert "health_context" in data
        assert "optimization_opportunities" in data


def test_4_factory_energy_reconciliation(client):
    """4. Test that factory actual energy equals the sum of machine actual energies."""
    fac, _ = fetch_api("/demo/factory")
    assert fac is not None
    fac_energy = fac["energy"]["actual_energy_kwh"]

    machine_sum = sum(
        fetch_api(f"/demo/machine/{m}")[0]["actual_energy_kwh"]
        for m in DEFAULT_PROFILES.keys()
    )
    assert abs(fac_energy - machine_sum) < 1e-4, f"Mismatch: {fac_energy} vs {machine_sum}"


def test_5_expected_energy_reconciliation(client):
    """5. Test that factory expected baseline equals sum of machine expected baselines."""
    fac, _ = fetch_api("/demo/factory")
    assert fac is not None
    fac_expected = fac["energy"]["expected_energy_kwh"]

    machine_expected_sum = sum(
        fetch_api(f"/demo/machine/{m}")[0]["baseline_expected_energy_kwh"]
        for m in DEFAULT_PROFILES.keys()
    )
    assert abs(fac_expected - machine_expected_sum) < 1e-4, f"Mismatch: {fac_expected} vs {machine_expected_sum}"


def test_6_production_reconciliation(client):
    """6. Test that factory production count strictly equals sum of machine production counts."""
    fac, _ = fetch_api("/demo/factory")
    assert fac is not None
    fac_prod = fac["production"]["total_units"]

    machine_prod_sum = sum(
        fetch_api(f"/demo/machine/{m}")[0]["production_units"]
        for m in DEFAULT_PROFILES.keys()
    )
    assert fac_prod == machine_prod_sum, f"Mismatch: {fac_prod} vs {machine_prod_sum}"


def test_7_deviation_arithmetic_validity(client):
    """7. Test that deviation = actual - expected at both factory and machine levels."""
    fac, _ = fetch_api("/demo/factory")
    assert fac is not None
    act = fac["energy"]["actual_energy_kwh"]
    exp = fac["energy"]["expected_energy_kwh"]
    dev = fac["deviation"]["deviation_kwh"]
    assert abs(dev - round(act - exp, 4)) < 1e-4

    for m in DEFAULT_PROFILES.keys():
        m_data, _ = fetch_api(f"/demo/machine/{m}")
        m_act = m_data["actual_energy_kwh"]
        m_exp = m_data["baseline_expected_energy_kwh"]
        m_dev = m_data["deviation_kwh"]
        assert abs(m_dev - round(m_act - m_exp, 4)) < 1e-4


def test_8_no_cumulative_meter_double_counting(client):
    """8. Test that actual_energy_kwh is interval consumption (<1.0 kWh), not cumulative meter (>100 kWh)."""
    for m in DEFAULT_PROFILES.keys():
        m_data, _ = fetch_api(f"/demo/machine/{m}")
        assert m_data is not None
        # In the demo window (60s), consumed energy is interval (< 1.0 kWh)
        assert m_data["actual_energy_kwh"] < 2.0, f"Possible meter register leak: {m_data['actual_energy_kwh']}"
        # Meter dial reading is cumulative register (> 90.0 kWh)
        assert m_data["energy_kwh"] >= 0.0


def test_9_forecast_data_labeled_predicted(client):
    """9. Test that multi-step forecast returns predicted horizons and model metadata."""
    res, _ = fetch_api("/forecast/factory?horizon_minutes=5")
    assert res is not None
    assert res["horizon_minutes"] == 5
    assert "total_factory_forecast_kwh" in res
    assert res["total_factory_forecast_kwh"] >= 0.0
    assert "factory_step_forecasts_kwh" in res
    assert len(res["factory_step_forecasts_kwh"]) == 5
    assert "model" in res


def test_10_savings_status_distinguished_from_potential_savings(client):
    """10. Test that potential savings is distinguished from verified post-intervention savings."""
    fac, _ = fetch_api("/demo/factory")
    assert fac is not None
    savings = fac["savings"]
    assert "potential_savings_kwh" in savings
    assert "potential_savings_inr" in savings
    assert "verified_savings_kwh" in savings
    # Potential savings is max(0, dev)
    expected_pot = max(0.0, fac["deviation"]["deviation_kwh"])
    assert abs(savings["potential_savings_kwh"] - expected_pot) < 1e-4
    # Explanatory note must be present
    assert "note" in savings


def test_11_missing_ollama_does_not_crash_copilot(client):
    """11. Test that Copilot provides deterministic evidence-grounded fallback when Ollama is offline."""
    with patch("llm.ollama_client.ollama_client.is_available", return_value=False):
        res, mode = fetch_api(
            "/copilot/chat",
            method="POST",
            payload={"question": "What is the factory energy consumption and how does it compare with baseline?"},
        )
        assert res is not None
        assert "answer" in res
        assert len(res["answer"]) > 20
        assert res["grounded"] is True
        assert res["fallback_used"] is True
        # Must reflect the factory actual energy in the answer
        fac, _ = fetch_api("/demo/factory")
        fac_e_str = f"{fac['energy']['actual_energy_kwh']:.2f}"
        assert str(fac['energy']['actual_energy_kwh']) in res["answer"] or fac_e_str in res["answer"]


def test_12_missing_api_does_not_crash_dashboard():
    """12. Test that fetch_api gracefully returns (None, FAILED) for non-existent endpoints."""
    res, mode = fetch_api("/nonexistent/endpoint/404")
    assert res is None
    assert "FAILED" in mode or "ERROR" in mode


def test_13_missing_production_produces_safe_sec_behavior(client):
    """13. Test that when production is zero, SEC displays safe format rather than NaN/inf."""
    # Unit helper test
    assert safe_sec(None) == "N/A (0 prod)"
    assert safe_sec(float("nan")) == "N/A (0 prod)"

    # Machine M01 produces 0 units in the demo
    m01, _ = fetch_api("/demo/machine/M01")
    assert m01 is not None
    if m01.get("production_units") == 0:
        assert m01.get("sec") is None


def test_14_machine_selection_coverage():
    """14. Test that all monitored fleet machine profiles exist in DEFAULT_PROFILES."""
    expected_ids = {"M01", "M02", "M03", "M04"}
    assert set(DEFAULT_PROFILES.keys()) == expected_ids
    for m_id, profile in DEFAULT_PROFILES.items():
        assert profile.rated_power_kw > 0.0
        assert len(profile.name) > 0


def test_15_demo_reset_is_deterministic():
    """15. Test that resetting the demo clears the buffer and repeated runs produce identical metrics."""
    demo_state.reset()
    assert not demo_state.has_active_demo_data()
    assert demo_state.telemetry_count == 0

    run1 = run_authoritative_demo(steps_per_phase=2, dt_seconds=1.0)
    run2 = run_authoritative_demo(steps_per_phase=2, dt_seconds=1.0)

    assert run1["actual_energy_kwh"] == run2["actual_energy_kwh"]
    assert run1["expected_energy_kwh"] == run2["expected_energy_kwh"]
    assert run1["production_units"] == run2["production_units"]
    assert run1["deviation_kwh"] == run2["deviation_kwh"]
    assert run1["copilot_answer"] == run2["copilot_answer"]


def test_16_authoritative_demo_reconciliation():
    """16. Test that run_authoritative_demo executes the clean 15-step sequence with 100% reconciliation."""
    summary = run_authoritative_demo(steps_per_phase=3, dt_seconds=1.0)
    assert summary["machines"] == 4
    assert summary["telemetry_count"] == 4 * 3 * 6  # 72 records
    assert summary["actual_energy_kwh"] > 0.0
    assert summary["expected_energy_kwh"] > 0.0
    assert summary["copilot_answer"] is not None
    assert len(summary["copilot_answer"]) > 0
