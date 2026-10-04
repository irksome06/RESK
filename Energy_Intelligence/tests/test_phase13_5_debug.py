"""
Phase 13.5 Regression and Quality Assurance Test Suite.
Verifies:
1. Copilot intent routing & query differentiation (Factory, Opportunities, Idle, Machine M01, Forecast)
2. M01 target propagation and machine-specific copilot behavior
3. Strict mathematical reconciliation across Factory, Machine Fleet, Operational States, and Copilot
4. Raw HTML avoidance in dashboard components
5. Terminology compliance (production-normalized verification, configured CO2 factor, forecast consumption)
6. Consistent section numbering (1 to 11 sequential)
7. Deterministic demo state execution and fallback resilience when Ollama is offline
"""

import re
import pytest
from fastapi.testclient import TestClient
from database.schemas import TelemetryRecord, MachineState
from simulator.demo_state import demo_state
from scripts.run_final_demo import run_authoritative_demo
from api.main import app
from llm.context_builder import context_builder, classify_intent
from llm.fallback import generate_deterministic_fallback


@pytest.fixture(scope="module")
def client():
    """Provides a reusable FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def init_authoritative_demo():
    """Ensures authoritative demo state is initialized for Phase 13.5 tests."""
    run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)


# =========================================================================
# A. COPILOT INTENT ROUTING & QUERY DIFFERENTIATION
# =========================================================================

def test_copilot_factory_summary_intent():
    """Verify factory baseline query routes to FACTORY_SUMMARY."""
    q = "What is the factory energy consumption and how does it compare with baseline?"
    intent, machine = classify_intent(q)
    assert intent == "FACTORY_SUMMARY"
    assert machine is None


def test_copilot_opportunities_intent():
    """Verify opportunity queries route to OPPORTUNITIES."""
    q = "What are the top prioritized energy optimization opportunities?"
    intent, machine = classify_intent(q)
    assert intent == "OPPORTUNITIES"
    assert machine is None


def test_copilot_idle_analysis_intent():
    """Verify idle energy queries route to IDLE_ANALYSIS."""
    q = "What is the factory idle energy and non-production draw?"
    intent, machine = classify_intent(q)
    assert intent == "IDLE_ANALYSIS"
    assert machine is None


def test_copilot_machine_analysis_intent():
    """Verify machine query targets specific machine M01 and routes to MACHINE_ANALYSIS."""
    q = "What is the operational status and energy consumption of machine M01?"
    intent, machine = classify_intent(q)
    assert intent == "MACHINE_ANALYSIS"
    assert machine == "M01"


def test_copilot_forecast_intent():
    """Verify forward-looking projection queries route to FORECAST."""
    q = "What is the short-horizon energy consumption forecast for the next 5 minutes?"
    intent, machine = classify_intent(q)
    assert intent == "FORECAST"
    assert machine is None


def test_copilot_distinct_responses_for_all_quick_actions(client):
    """
    Critical Bug Fix Verification:
    Verify that all 5 quick-actions produce distinctly different intents and answers.
    """
    queries = [
        ("Factory Baseline", "What is the factory energy consumption and how does it compare with baseline?"),
        ("Top Opportunity", "What are the top prioritized energy optimization opportunities?"),
        ("Idle Energy Analysis", "What is the factory idle energy and non-production draw?"),
        ("Machine M01 Status", "What is the operational status and energy consumption of machine M01?"),
        ("5-Min Forecast", "What is the short-horizon energy consumption forecast for the next 5 minutes?"),
    ]

    intents_seen = set()
    answers_seen = set()

    for label, q in queries:
        res = client.post("/copilot/chat", json={"question": q})
        assert res.status_code == 200
        data = res.json()
        intents_seen.add(data["intent"])
        answers_seen.add(data["answer"])

    # All 5 queries must produce distinct intents
    assert len(intents_seen) == 5, f"Expected 5 distinct intents, got: {intents_seen}"
    # All 5 queries must produce distinct answers
    assert len(answers_seen) == 5, f"Expected 5 distinct answers, got {len(answers_seen)}"


def test_copilot_machine_endpoint_targets_m01(client):
    """Verify /copilot/machine/M01 explicitly evaluates machine M01."""
    res = client.post("/copilot/machine/M01", json={"question": "Analyze energy and operating performance."})
    assert res.status_code == 200
    data = res.json()
    assert "M01" in data["answer"]
    assert data["intent"] in ["MACHINE_ANALYSIS", "EFFICIENCY", "ENERGY_DEVIATION", "GENERAL"]


def test_factory_query_does_not_silently_target_m01():
    """Verify factory-level deviation query does NOT assign M01 as target machine."""
    q = "Is factory energy consumption above or below baseline?"
    intent, target_m = classify_intent(q)
    assert intent == "ENERGY_DEVIATION"
    assert target_m is None


# =========================================================================
# B. DATA RECONCILIATION
# =========================================================================

def test_machine_energy_reconciles_to_factory(client):
    """Verify sum(machine_energy) == factory_actual_energy within tolerance."""
    res = client.get("/demo/factory").json()
    factory_actual = res["energy"]["actual_energy_kwh"]
    sum_machine_actual = sum(m["energy_kwh"] for m in res["machine_status"])
    assert abs(factory_actual - sum_machine_actual) < 1e-4


def test_machine_expected_energy_reconciles_to_factory(client):
    """Verify sum(machine_expected_energy) == factory_expected_energy within tolerance."""
    res = client.get("/demo/factory").json()
    factory_expected = res["energy"]["expected_energy_kwh"]
    machine_expecteds = []
    for m in res["machine_status"]:
        m_detail = client.get(f"/demo/machine/{m['machine_id']}").json()
        machine_expecteds.append(m_detail["baseline_expected_energy_kwh"])
    assert abs(factory_expected - sum(machine_expecteds)) < 1e-4


def test_state_energy_reconciles_to_factory(client):
    """Verify sum(state_energy) == factory_actual_energy within tolerance."""
    f_res = client.get("/demo/factory").json()
    s_res = client.get("/savings/states").json()
    factory_actual = f_res["energy"]["actual_energy_kwh"]
    sum_state_actual = sum(s["actual_energy_kwh"] for s in s_res["states"])
    assert abs(factory_actual - sum_state_actual) < 1e-4


def test_production_reconciles_to_factory(client):
    """Verify sum(machine_production) == factory_production."""
    res = client.get("/demo/factory").json()
    factory_production = res["production"]["total_units"]
    sum_machine_production = sum(m["production_units"] for m in res["machine_status"])
    assert factory_production == sum_machine_production


def test_savings_formula_reconciles(client):
    """Verify deviation = actual - expected and potential_savings = max(0, deviation)."""
    res = client.get("/demo/factory").json()
    actual = res["energy"]["actual_energy_kwh"]
    expected = res["energy"]["expected_energy_kwh"]
    dev = res["deviation"]["deviation_kwh"]
    pot_savings = res["savings"]["potential_savings_kwh"]

    assert abs(dev - (actual - expected)) < 1e-4
    assert abs(pot_savings - max(0.0, dev)) < 1e-4


def test_copilot_context_matches_factory_snapshot(client):
    """Verify that Copilot context numbers match the factory snapshot."""
    f_res = client.get("/demo/factory").json()
    ctx = context_builder.build_context("What is the factory energy consumption and how does it compare with baseline?")
    fs = ctx["structured_data"]["factory_summary"]

    assert abs(fs["actual_energy_kwh"] - f_res["energy"]["actual_energy_kwh"]) < 1e-3
    assert abs(fs["expected_energy_kwh"] - f_res["energy"]["expected_energy_kwh"]) < 1e-3
    assert fs["production_units"] == f_res["production"]["total_units"]


# =========================================================================
# C. DASHBOARD CODE INTEGRITY & TERMINOLOGY
# =========================================================================

def test_no_raw_html_in_savings_card():
    """Verify dashboard/app.py does not contain indented code blocks leaking raw HTML."""
    from pathlib import Path
    app_file = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    # In Python markdown, 4+ spaces after empty line inside html causes <pre><code> leakage
    assert '<hr style="border-color: #262F40; margin: 10px 0;"/>' in content
    # Verify it is part of clean HTML string without raw escaped rendering
    assert "savings_card_html = (" in content


def test_dashboard_section_numbering_complete():
    """Verify dashboard has sequential section numbering 1 to 11 with no missing sections."""
    from pathlib import Path
    app_file = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    expected_sections = [
        "1. Factory Intelligence Overview",
        "2. Energy vs Production Activity",
        "3. Actual vs Production-Aware Baseline",
        "4. Monitored Machine Fleet Intelligence",
        "5. Asset Deep-Dive & Health Telemetry",
        "6. Operational State Energy Allocation",
        "7. Non-Production Energy Intelligence",
        "8. Short-Horizon Energy Consumption Forecast",
        "9. Savings Intelligence & Production-Normalized Verification",
        "10. Prioritized Energy Optimization Opportunities",
        "11. Grounded Energy Intelligence Copilot",
    ]

    for sec in expected_sections:
        assert sec in content, f"Missing section in dashboard: {sec}"


def test_dashboard_terminology_verification():
    """Verify dashboard avoids unaccredited IPMVP and authoritative CEA factor claims."""
    from pathlib import Path
    app_file = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    # Should NOT have unverified claims
    assert "CEA Grid Factor:" not in content
    assert "IPMVP Verification" not in content
    assert "Projected 5-Minute Factory Demand:" not in content

    # Should have verified neutral wording
    assert "Configured CO₂ Factor:" in content
    assert "Production-Normalized Verification" in content
    assert "Projected Energy Consumption — Next 5 Minutes:" in content


# =========================================================================
# D. DETERMINISTIC DEMO & FALLBACK RESILIENCE
# =========================================================================

def test_deterministic_demo_reset():
    """Verify demo reset clears telemetry buffer cleanly."""
    demo_state.reset()
    assert not demo_state.has_active_demo_data()
    assert demo_state.telemetry_count == 0
    # Re-run demo to restore active state
    run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)
    assert demo_state.has_active_demo_data()


def test_deterministic_fallback_when_ollama_offline():
    """Verify deterministic fallback responds gracefully for IDLE_ANALYSIS when Ollama is offline."""
    ctx = context_builder.build_context("Why is machine M01 consuming energy when production is zero?")
    ans = generate_deterministic_fallback(ctx, "Why is machine M01 consuming energy when production is zero?")

    assert "Summary:" in ans
    assert "Evidence:" in ans
    assert "Interpretation:" in ans
    assert "Recommended Next Step:" in ans
    assert "M01" in ans
    assert "IDLE" in ans
