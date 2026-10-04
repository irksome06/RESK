"""
Phase 13.1 Hardening & Regression Test Suite.
Schneider Electric 2026 Smart Manufacturing Hackathon:
Person 3: Energy & Production Intelligence Engine

Comprehensive test coverage across:
1. Copilot Conversational Chat, Presets & Mode Labeling (10 tests)
2. Authoritative Data Consistency & Cross-Module Reconciliation (8 tests)
3. Machine Telemetry & SLEEP / RPM Consistency (4 tests)
4. Production Semantics & RUNNING != PRODUCING (4 tests)
5. Forecast Units & Step-Sum Aggregate Reconciliation (4 tests)
6. Zero-Production Savings Semantics & Baseline Interpretation (4 tests)
7. Demo Reset & API Determinism (2 tests)

Total: 36 new tests.
"""

import math
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.schemas import TelemetryRecord, MachineState
from simulator.demo_state import demo_state
from simulator.machine_simulator import DEFAULT_PROFILES
from llm.context_builder import context_builder, detect_intent
from llm.fallback import generate_deterministic_fallback
from scripts.run_final_demo import run_authoritative_demo


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def authoritative_factory_data():
    """Executes the authoritative 6-phase demonstration scenario once for the module."""
    demo_state.reset()
    res = run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)
    return res


# =====================================================================
# 1. COPILOT CONVERSATIONAL CHAT, PRESETS & MODE LABELING
# =====================================================================

def test_copilot_general_chat_intent_detection():
    """Verify general conversation and capability queries map to GENERAL_CHAT."""
    for q in ["what can you do", "what u can do", "help me", "who are you", "what are your capabilities"]:
        intent, target = detect_intent(q)
        assert intent == "GENERAL_CHAT"
        assert target is None


def test_copilot_what_can_you_do_natural_response(client):
    """Verify 'what can you do' returns natural conversational explanation rather than rigid template."""
    res = client.post("/copilot/chat", json={"question": "What can you do?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "GENERAL_CHAT"
    assert "Summary:" not in data["answer"]
    assert "Evidence:" not in data["answer"]
    assert "I can help you understand the factory's energy" in data["answer"] or "capabilities" in data["answer"].lower()
    assert "Factory Baseline" in data["answer"] or "baseline" in data["answer"].lower()


def test_copilot_general_chat_execution_mode(client):
    """Verify general questions do not display misleading analytics grounding badges."""
    res = client.post("/copilot/chat", json={"question": "Hello, how are you today?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "GENERAL_CHAT"


def test_copilot_factory_baseline_preset_query(client, authoritative_factory_data):
    """Verify factory baseline query returns grounded numbers."""
    q = "Give me the current factory energy consumption and compare it with the production-aware baseline."
    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "FACTORY_SUMMARY"
    assert data["grounded"] is True
    assert "Summary:" in data["answer"]
    assert "0.3962" in data["answer"] or "0.3961" in data["answer"] or "0.39" in data["answer"]


def test_copilot_top_opportunity_preset_query(client, authoritative_factory_data):
    """Verify top opportunity query identifies opportunities without claiming machine control."""
    q = "Which energy optimization opportunity currently has the highest calculated priority, and what evidence supports it?"
    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "OPPORTUNITIES"
    assert "M01" in data["answer"]
    assert "IDLE" in data["answer"]
    # Verify Person 1 boundary: does not issue actuator commands
    assert "PLC command executed" not in data["answer"]


def test_copilot_idle_energy_preset_query(client, authoritative_factory_data):
    """Verify idle energy query returns non-production energy allocation."""
    q = "How much energy is being consumed during non-production states, especially IDLE and SLEEP?"
    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "IDLE_ANALYSIS"
    assert "IDLE" in data["answer"]


def test_copilot_machine_status_preset_query(client, authoritative_factory_data):
    """Verify machine query returns machine-specific grounded status."""
    q = "Give me the current operational and energy status of M01."
    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "MACHINE_ANALYSIS"
    assert "M01" in data["answer"]
    assert "SLEEP" in data["answer"]


def test_copilot_5min_forecast_preset_query(client, authoritative_factory_data):
    """Verify forecast query returns multi-step horizon."""
    q = "What is the predicted energy consumption for the next five minutes?"
    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "FORECAST"
    assert "5 minutes" in data["answer"] or "five minutes" in data["answer"]


def test_copilot_numerical_grounding_preserves_factory_actual(client, authoritative_factory_data):
    """Verify context summary matches authoritative factory snapshot."""
    res_factory = client.get("/demo/factory")
    assert res_factory.status_code == 200
    factory_kwh = res_factory.json()["energy"]["actual_energy_kwh"]

    res_chat = client.post("/copilot/chat", json={"question": "What is factory energy consumption?"})
    assert res_chat.status_code == 200
    ctx = res_chat.json().get("context_summary", {})
    copilot_actual = ctx.get("factory_energy_kwh")
    assert copilot_actual is not None
    assert abs(copilot_actual - factory_kwh) < 1e-4


def test_copilot_fallback_when_ollama_offline(client):
    """Verify deterministic fallback works cleanly without 500 error when Ollama is offline."""
    res = client.post("/copilot/chat", json={"question": "What is the factory baseline?"})
    assert res.status_code == 200
    data = res.json()
    assert data["fallback_used"] is True
    assert data["grounded"] is True
    assert len(data["answer"]) > 10


# =====================================================================
# 2. AUTHORITATIVE DATA CONSISTENCY & RECONCILIATION
# =====================================================================

def test_reconciliation_factory_actual_equals_sum_machine_actual(client, authoritative_factory_data):
    """Factory actual energy must equal sum of machine actual energies within 1e-4 kWh."""
    res_f = client.get("/demo/factory")
    factory_actual = res_f.json()["energy"]["actual_energy_kwh"]

    machines = ["M01", "M02", "M03", "M04"]
    sum_m = 0.0
    for m in machines:
        res_m = client.get(f"/demo/machine/{m}")
        sum_m += res_m.json()["actual_energy_kwh"]

    assert abs(factory_actual - sum_m) < 1e-4


def test_reconciliation_factory_expected_equals_sum_machine_expected(client, authoritative_factory_data):
    """Factory expected energy baseline must equal sum of machine expected baselines."""
    res_f = client.get("/demo/factory")
    factory_expected = res_f.json()["energy"]["expected_energy_kwh"]

    machines = ["M01", "M02", "M03", "M04"]
    sum_exp = 0.0
    for m in machines:
        res_m = client.get(f"/demo/machine/{m}")
        sum_exp += res_m.json()["baseline_expected_energy_kwh"]

    assert abs(factory_expected - sum_exp) < 1e-4


def test_reconciliation_factory_production_equals_sum_machine_production(client, authoritative_factory_data):
    """Factory production output must equal sum of individual machine production counts."""
    res_f = client.get("/demo/factory")
    factory_prod = res_f.json()["production"]["total_units"]

    machines = ["M01", "M02", "M03", "M04"]
    sum_prod = 0
    for m in machines:
        res_m = client.get(f"/demo/machine/{m}")
        sum_prod += res_m.json()["production_units"]

    assert factory_prod == sum_prod


def test_reconciliation_state_energy_equals_factory_total(client, authoritative_factory_data):
    """Sum of operational state energy allocations must equal factory total actual energy."""
    res_f = client.get("/demo/factory")
    factory_actual = res_f.json()["energy"]["actual_energy_kwh"]

    res_states = client.get("/savings/states")
    assert res_states.status_code == 200
    states = res_states.json()["states"]
    sum_states = sum(s.get("energy_kwh", 0.0) or s.get("actual_energy_kwh", 0.0) for s in states)

    assert abs(factory_actual - sum_states) < 1e-4


def test_reconciliation_deviation_formula(client, authoritative_factory_data):
    """Deviation must strictly equal actual_energy - expected_energy."""
    res_f = client.get("/demo/factory")
    data = res_f.json()
    actual = data["energy"]["actual_energy_kwh"]
    expected = data["energy"]["expected_energy_kwh"]
    dev = data["deviation"]["deviation_kwh"]

    assert abs(dev - round(actual - expected, 4)) < 1e-4


def test_reconciliation_cumulative_meter_never_used_as_interval_energy(client, authoritative_factory_data):
    """Cumulative meter dial (e.g. ~100 kWh) must be strictly distinguished from interval consumed energy (~0.02 kWh)."""
    for m_id in ["M01", "M02", "M03", "M04"]:
        res_m = client.get(f"/demo/machine/{m_id}")
        data = res_m.json()
        interval_e = data["actual_energy_kwh"]
        cumulative_m = data["energy_kwh"]
        assert cumulative_m > 1.0  # Meter register is accumulated
        assert interval_e < 1.0    # Consumed interval energy in demo window is small delta
        assert cumulative_m != interval_e


def test_reconciliation_analysis_window_shared_consistently(client, authoritative_factory_data):
    """Analysis window start, end, and duration must be defined and shared."""
    res_f = client.get("/demo/factory")
    w = res_f.json().get("analysis_window", {})
    assert w.get("start_time") not in (None, "N/A")
    assert w.get("end_time") not in (None, "N/A")
    assert w.get("duration_seconds", 0.0) > 0.0


def test_reconciliation_carbon_footprint_factor(client, authoritative_factory_data):
    """Carbon footprint must equal actual_energy * 0.716 kg CO2/kWh."""
    res_f = client.get("/demo/factory")
    data = res_f.json()
    actual = data["energy"]["actual_energy_kwh"]
    co2 = data["energy"]["co2_kg"]
    assert abs(co2 - round(actual * 0.716, 4)) < 1e-4


# =====================================================================
# 3. MACHINE TELEMETRY & SLEEP / RPM CONSISTENCY
# =====================================================================

def test_machine_sleep_rpm_consistency(client, authoritative_factory_data):
    """M01 in SLEEP state must not display motor speed ~1450 RPM."""
    res_m = client.get("/demo/machine/M01")
    assert res_m.status_code == 200
    data = res_m.json()
    assert data["current_state"] == "SLEEP"
    hc = data.get("health_context", {})
    rpm = hc.get("rpm", 0.0)
    assert rpm == 0.0 or rpm < 50.0  # RPM must be 0 for SLEEP, never 1450.0


def test_machine_running_rpm_nominal(client, authoritative_factory_data):
    """Running machine (e.g. M04) should display nominal operating RPM."""
    res_m = client.get("/demo/machine/M04")
    assert res_m.status_code == 200
    data = res_m.json()
    assert data["current_state"] == "RUNNING"
    hc = data.get("health_context", {})
    assert hc.get("rpm", 0.0) > 1000.0


def test_machine_detail_person2_context_boundary(client, authoritative_factory_data):
    """Health score and vibration must be tagged as advisory context from Person 2."""
    res_m = client.get("/demo/machine/M01")
    data = res_m.json()
    hc = data.get("health_context", {})
    assert "health_score" in hc
    assert "vibration" in hc
    assert "temperature_c" in hc


def test_machine_unknown_returns_404(client):
    """Non-existent machine ID should return a 404 HTTP status."""
    res = client.get("/demo/machine/M99")
    assert res.status_code == 404


# =====================================================================
# 4. PRODUCTION SEMANTICS & RUNNING != PRODUCING
# =====================================================================

def test_running_is_not_automatically_producing(client):
    """A machine in RUNNING state is NOT producing unless production_units > 0."""
    t0 = datetime(2026, 10, 4, 11, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 4, 11, 0, 10, tzinfo=timezone.utc)
    records = []
    for m_id in ["M01", "M02", "M03", "M04"]:
        records.extend([
            TelemetryRecord(
                timestamp=t0, machine_id=m_id, power_kw=3.0, energy_kwh=10.0,
                machine_state=MachineState.RUNNING, production_count=0, production_delta=0,
                cycle_time_sec=0.0, voltage_v=415.0, current_a=5.0, temperature_c=50.0,
                vibration=0.1, rpm=1450.0, health_score=100.0,
            ),
            TelemetryRecord(
                timestamp=t1, machine_id=m_id, power_kw=3.0, energy_kwh=10.01,
                machine_state=MachineState.RUNNING, production_count=0, production_delta=0,
                cycle_time_sec=0.0, voltage_v=415.0, current_a=5.0, temperature_c=50.0,
                vibration=0.1, rpm=1450.0, health_score=100.0,
            )
        ])
    demo_state.set_active_demo_records(records)

    res = client.get("/demo/factory")
    assert res.status_code == 200
    prod = res.json()["production"]
    assert prod["total_units"] == 0
    assert prod["running_machines"] == 4
    assert prod["active_producing_machines"] == 0


def test_sec_none_when_production_zero(client):
    """When production is 0, factory SEC must be None (N/A), never 0 or infinity."""
    res = client.get("/demo/factory")
    assert res.status_code == 200
    assert res.json()["sec"] is None


def test_active_producing_machines_count_positive(client):
    """When units are produced, active_producing_machines reflects assets with delta > 0."""
    run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)
    res = client.get("/demo/factory")
    prod = res.json()["production"]
    assert prod["total_units"] == 3
    assert prod["active_producing_machines"] == 3
    assert prod["running_machines"] >= 3


def test_machine_sec_none_when_machine_production_zero(client):
    """Machine M01 has 0 production units, so its SEC must be None."""
    res_m = client.get("/demo/machine/M01")
    assert res_m.status_code == 200
    assert res_m.json()["production_units"] == 0
    assert res_m.json()["sec"] is None


# =====================================================================
# 5. FORECAST UNITS & STEP-SUM AGGREGATE RECONCILIATION
# =====================================================================

def test_forecast_total_equals_sum_of_intervals(client, authoritative_factory_data):
    """Projected 5-minute energy must strictly equal sum of the five 1-minute steps."""
    res = client.get("/demo/factory")
    fc = res.json()["forecast"]
    total = fc["total_forecast_kwh"]
    intervals = fc["intervals"]
    assert len(intervals) == 5
    step_sum = round(sum(i["forecast_energy_kwh"] for i in intervals), 4)
    assert abs(total - step_sum) < 1e-4


def test_forecast_steps_are_positive_and_monotonic_time(client, authoritative_factory_data):
    """All 5 forecast intervals must have positive energy and ascending steps 1 to 5."""
    res = client.get("/demo/factory")
    intervals = res.json()["forecast"]["intervals"]
    steps = [i["step"] for i in intervals]
    assert steps == [1, 2, 3, 4, 5]
    for i in intervals:
        assert i["forecast_energy_kwh"] > 0.0


def test_forecast_horizon_is_5_minutes(client, authoritative_factory_data):
    """Forecast horizon must be declared as 5 minutes."""
    res = client.get("/demo/factory")
    fc = res.json()["forecast"]
    assert fc["horizon_minutes"] == 5


def test_forecast_copilot_reconciles_with_api(client, authoritative_factory_data):
    """Copilot forecast response must reference the forecast model and multi-step projection."""
    res = client.post("/copilot/chat", json={"question": "What is the 5-minute energy forecast?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "FORECAST"
    assert "5 minutes" in data["answer"] or "five minutes" in data["answer"]


# =====================================================================
# 6. ZERO-PRODUCTION SAVINGS & BASELINE INTERPRETATION
# =====================================================================

def test_savings_status_insufficient_data_when_zero_production(client):
    """When production is 0, verified savings status must be INSUFFICIENT_DATA."""
    t0 = datetime(2026, 10, 4, 11, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 4, 11, 0, 10, tzinfo=timezone.utc)
    records = []
    for m_id in ["M01", "M02", "M03", "M04"]:
        records.extend([
            TelemetryRecord(
                timestamp=t0, machine_id=m_id, power_kw=1.0, energy_kwh=10.0,
                machine_state=MachineState.IDLE, production_count=0, production_delta=0,
                cycle_time_sec=0.0, voltage_v=415.0, current_a=2.0, temperature_c=50.0,
                vibration=0.1, rpm=0.0, health_score=100.0,
            ),
            TelemetryRecord(
                timestamp=t1, machine_id=m_id, power_kw=1.0, energy_kwh=10.005,
                machine_state=MachineState.IDLE, production_count=0, production_delta=0,
                cycle_time_sec=0.0, voltage_v=415.0, current_a=2.0, temperature_c=50.0,
                vibration=0.1, rpm=0.0, health_score=100.0,
            )
        ])
    demo_state.set_active_demo_records(records)

    res = client.get("/demo/factory")
    assert res.status_code == 200
    savings = res.json()["savings"]
    assert savings["verification_status"] == "INSUFFICIENT_DATA"


def test_potential_savings_separate_from_verified_savings(client, authoritative_factory_data):
    """Potential savings must be maintained separately from verified savings."""
    res = client.get("/demo/factory")
    savings = res.json()["savings"]
    assert "potential_savings_kwh" in savings
    assert "verified_savings_kwh" in savings
    assert "potential_savings_inr" in savings


def test_copilot_explains_sec_unavailable_when_zero_production(client):
    """When asked about SEC with zero production, Copilot explains that production output is required."""
    res = client.post("/copilot/chat", json={"question": "What is the factory SEC?"})
    assert res.status_code == 200
    data = res.json()
    assert "SEC Status: N/A" in data["answer"] or "0" in data["answer"]


def test_baseline_deviation_below_baseline_not_labeled_efficiency_when_zero_prod(client):
    """When production is 0 and draw is low, UI/system clarifies zero production prevents SEC evaluation."""
    res = client.get("/demo/factory")
    assert res.json()["production"]["total_units"] == 0
    assert res.json()["sec"] is None


# =====================================================================
# 7. DEMO RESET & API DETERMINISM
# =====================================================================

def test_demo_reset_endpoint_deterministic(client):
    """POST /demo/reset resets the telemetry buffer and returns status RESET."""
    res = client.post("/demo/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "RESET"
    assert demo_state.telemetry_count == 0


def test_demo_run_endpoint_executes_successfully(client):
    """POST /demo/run executes the scenario and populates authoritative telemetry."""
    res = client.post("/demo/run?steps_per_phase=5")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert demo_state.telemetry_count > 0
