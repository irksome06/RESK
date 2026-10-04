"""
Phase 13.6 Copilot & Dashboard Integrity Test Suite.
Verifies:
1. Dynamic Copilot responses (answers change dynamically with authoritative data, no hardcoded answers).
2. Clean separation between FACTORY_DOMAIN and GENERAL_CHAT.
3. Personal/general questions do not leak factory energy metrics or invent identity.
4. Single source of truth for Machine IDs & Names (DEFAULT_PROFILES vs Dashboard).
5. Authoritative demo window for IDLE/SLEEP state energy.
6. Opportunity engine detects qualifying events in authoritative demo window.
7. Provenance labels (Expected is [PREDICTED], Deviation is [CALCULATED]).
8. Zero Hallucination claim removed and replaced with PASSED grounding validation.
9. Paraphrased intent routing for industrial and non-industrial domains.
10. End-to-end data reconciliation guarantees intact.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from api.main import app
from simulator.machine_simulator import DEFAULT_PROFILES, MachineProfile
from simulator.demo_state import demo_state
from database.schemas import TelemetryRecord, MachineState
from llm.context_builder import classify_intent, context_builder
from llm.fallback import generate_deterministic_fallback
from llm.validation import validate_copilot_response
from analytics.efficiency import compute_state_efficiency, compute_factory_efficiency, compute_machine_efficiency
from analytics.savings import compute_machine_savings
from analytics.optimization import opportunity_engine
from dashboard.app import get_machine_display_name


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# 1. MACHINE ID & NAME SINGLE SOURCE OF TRUTH TESTS
# =========================================================================

def test_machine_names_canonical_single_source_of_truth():
    """Verify get_machine_display_name strictly matches DEFAULT_PROFILES."""
    for m_id, prof in DEFAULT_PROFILES.items():
        disp_name = get_machine_display_name(m_id)
        assert disp_name == f"{m_id} - {prof.name}"
        assert prof.name in disp_name


def test_m01_is_cnc_milling_center_not_stamping_press():
    """Verify M01 is CNC Milling Center across profiles and dashboard helpers."""
    assert "CNC Milling Center" in DEFAULT_PROFILES["M01"].name
    assert "Stamping Press" not in DEFAULT_PROFILES["M01"].name
    assert "CNC Milling Center" in get_machine_display_name("M01")


def test_machine_id_preserved_through_selection():
    """Verify selecting a display name cleanly recovers the exact machine ID."""
    for m_id in DEFAULT_PROFILES:
        disp = get_machine_display_name(m_id)
        extracted_id = disp.split(" - ")[0]
        assert extracted_id == m_id
        assert extracted_id in DEFAULT_PROFILES


# =========================================================================
# 2. GENERAL_CHAT VS FACTORY DOMAIN INTENT ROUTING
# =========================================================================

def test_personal_question_routes_to_general_chat():
    """Verify 'What is my name?' maps to GENERAL_CHAT without machine ID."""
    intent, m_id = classify_intent("What is my name?")
    assert intent == "GENERAL_CHAT"
    assert m_id is None


def test_identity_question_routes_to_general_chat():
    """Verify 'Who are you?' maps to GENERAL_CHAT."""
    intent, m_id = classify_intent("Who are you?")
    assert intent == "GENERAL_CHAT"
    assert m_id is None


def test_general_tech_questions_route_to_general_chat():
    """Verify generic tech/ML questions map to GENERAL_CHAT."""
    for q in [
        "What is machine learning?",
        "Explain Python.",
        "Tell me a joke.",
        "How does a neural network work?",
        "What does gradient boosting mean?",
        "Write an email.",
    ]:
        intent, m_id = classify_intent(q)
        assert intent == "GENERAL_CHAT", f"Query '{q}' routed to {intent} instead of GENERAL_CHAT"
        assert m_id is None


def test_factory_questions_route_to_factory_intents():
    """Verify industrial queries route to appropriate factory intents."""
    assert classify_intent("What is the factory energy consumption?")[0] == "FACTORY_SUMMARY"
    assert classify_intent("How much energy did M01 consume?")[0] == "MACHINE_ANALYSIS"
    assert classify_intent("What are the top energy optimization opportunities?")[0] == "OPPORTUNITIES"
    assert classify_intent("What is the energy forecast for the next 5 minutes?")[0] == "FORECAST"
    assert classify_intent("How much energy is being consumed while machines are idle?")[0] == "IDLE_ANALYSIS"


def test_paraphrased_intent_routing():
    """Verify paraphrases route to correct domain intents without hardcoded exact strings."""
    assert classify_intent("What is the plant's energy usage?")[0] == "FACTORY_SUMMARY"
    assert classify_intent("Which machines should we investigate for energy efficiency?")[0] == "OPPORTUNITIES"
    assert classify_intent("What's coming in the next five minutes?")[0] == "FORECAST"
    assert classify_intent("How much power are we wasting while machines wait?")[0] == "IDLE_ANALYSIS"
    assert classify_intent("Tell me about M02.")[0] == "MACHINE_ANALYSIS"
    assert classify_intent("What does gradient boosting mean?")[0] == "GENERAL_CHAT"


# =========================================================================
# 3. PERSONAL & GENERAL FALLBACK SAFEGUARDS (NO FACTORY LEAKAGE)
# =========================================================================

def test_personal_question_context_has_no_factory_metrics():
    """Verify build_context for personal query contains no factory kWh or grounded facts."""
    ctx = context_builder.build_context("What is my name?")
    assert ctx["intent"] == "GENERAL_CHAT"
    assert len(ctx["grounded_facts"]) == 0
    assert "actual_energy_kwh" not in ctx["structured_data"]
    assert "factory_summary" not in ctx["structured_data"]


def test_general_fallback_does_not_leak_factory_kpis():
    """Verify fallback for GENERAL_CHAT contains no factory energy figures."""
    for q in ["What is my name?", "What is machine learning?", "Explain Python.", "Who are you?"]:
        ctx = context_builder.build_context(q)
        ans = generate_deterministic_fallback(ctx, q)
        assert "0.3962" not in ans
        assert "0.7923" not in ans
        assert "kWh" not in ans
        assert "Factory electrical energy consumption is currently" not in ans


def test_personal_question_refuses_identity_invention():
    """Verify personal question explicitly declines personal identity knowledge."""
    ctx = context_builder.build_context("What is my name?")
    ans = generate_deterministic_fallback(ctx, "What is my name?")
    assert "do not possess personal profile information" in ans


# =========================================================================
# 4. DYNAMIC COPILOT ANSWER TEST (NO HARDCODED ANSWERS)
# =========================================================================

def test_dynamic_copilot_answers_change_with_telemetry():
    """
    Test concept:
    1. Populate demo state with Dataset A.
    2. Ask Factory Baseline question and capture numeric metrics in response.
    3. Modify demo state with Dataset B (different energy values).
    4. Ask the exact same Factory Baseline question.
    5. Verify context values and answer change dynamically.
    """
    from datetime import timedelta
    t0 = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1)

    # Dataset A: Realistic energy increments (~7 kW implied power)
    recs_a = {
        "M01": [
            TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=5.0, energy_kwh=10.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M01", power_kw=5.0, energy_kwh=10.002, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
        "M02": [
            TelemetryRecord(timestamp=t0, machine_id="M02", power_kw=4.0, energy_kwh=20.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M02", power_kw=4.0, energy_kwh=20.002, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
        "M03": [
            TelemetryRecord(timestamp=t0, machine_id="M03", power_kw=4.0, energy_kwh=30.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M03", power_kw=4.0, energy_kwh=30.002, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
        "M04": [
            TelemetryRecord(timestamp=t0, machine_id="M04", power_kw=3.0, energy_kwh=40.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M04", power_kw=3.0, energy_kwh=40.002, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
    }

    q = "What is the factory energy consumption and how does it compare with baseline?"
    ctx_a = context_builder.build_context(question=q, machine_records_override=recs_a)
    act_a = ctx_a["structured_data"]["factory_summary"]["actual_energy_kwh"]
    ans_a = generate_deterministic_fallback(ctx_a, q)

    # Dataset B: Higher energy increments (~21 kW implied power)
    recs_b = {
        "M01": [
            TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=5.0, energy_kwh=10.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M01", power_kw=5.0, energy_kwh=10.006, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
        "M02": [
            TelemetryRecord(timestamp=t0, machine_id="M02", power_kw=4.0, energy_kwh=20.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M02", power_kw=4.0, energy_kwh=20.006, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
        "M03": [
            TelemetryRecord(timestamp=t0, machine_id="M03", power_kw=4.0, energy_kwh=30.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M03", power_kw=4.0, energy_kwh=30.006, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
        "M04": [
            TelemetryRecord(timestamp=t0, machine_id="M04", power_kw=3.0, energy_kwh=40.0, machine_state=MachineState.RUNNING, production_count=10, production_delta=0),
            TelemetryRecord(timestamp=t1, machine_id="M04", power_kw=3.0, energy_kwh=40.006, machine_state=MachineState.RUNNING, production_count=11, production_delta=1),
        ],
    }

    ctx_b = context_builder.build_context(question=q, machine_records_override=recs_b)
    act_b = ctx_b["structured_data"]["factory_summary"]["actual_energy_kwh"]
    ans_b = generate_deterministic_fallback(ctx_b, q)

    assert act_a != act_b, f"Context actual energy should differ: {act_a} vs {act_b}"
    assert ans_a != ans_b, "Answer must reflect dynamic telemetry data changes, not static text."
    assert str(act_a) in ans_a
    assert str(act_b) in ans_b


# =========================================================================
# 5. IDLE / SLEEP ENERGY IN AUTHORITATIVE WINDOW
# =========================================================================

def test_authoritative_demo_window_state_energy_breakdown():
    """Verify IDLE, SLEEP, RUNNING energy contributions on authoritative demo window."""
    from scripts.run_final_demo import run_authoritative_demo
    run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)

    recs = demo_state.get_demo_records(machine_id=None)
    assert len(recs) == 240, f"Expected 240 demo records, got {len(recs)}"

    s_dict = compute_state_efficiency(recs)
    running_kwh = s_dict["RUNNING"]["actual_energy_kwh"]
    idle_kwh = s_dict["IDLE"]["actual_energy_kwh"]
    sleep_kwh = s_dict["SLEEP"]["actual_energy_kwh"]

    assert running_kwh > 0.0, "RUNNING energy must be > 0"
    assert idle_kwh > 0.0, "IDLE energy must be > 0"
    assert sleep_kwh > 0.0, "SLEEP energy must be > 0"

    tot_state_energy = sum(d["actual_energy_kwh"] for d in s_dict.values())
    rec_dict = demo_state.get_demo_records_dict()
    tot_machine_energy = sum(
        compute_machine_savings(m_recs)["actual_energy_kwh"]
        for m_recs in rec_dict.values()
    )

    assert abs(tot_state_energy - tot_machine_energy) < 1e-4, (
        f"State energy ({tot_state_energy}) must reconcile with machine energy ({tot_machine_energy})"
    )


def test_opportunity_engine_sees_authoritative_demo_window():
    """Verify opportunity engine identifies M01 IDLE event from authoritative demo records."""
    rec_dict = demo_state.get_demo_records_dict()
    opps = opportunity_engine.evaluate_factory(rec_dict)
    assert len(opps) > 0, "Opportunity engine should identify opportunities from demo scenario"
    categories = [o["category"] for o in opps]
    assert "IDLE_REDUCTION" in categories, "Expected IDLE_REDUCTION opportunity from M01 IDLE phase"


# =========================================================================
# 6. DASHBOARD CODE PROVENANCE & ZERO HALLUCINATION INSPECTION
# =========================================================================

def test_baseline_deviation_is_labeled_calculated_in_dashboard():
    """Verify Baseline Deviation is labeled [CALC] in dashboard/app.py."""
    with open("dashboard/app.py", "r") as f:
        content = f.read()

    # Section 5 metric card 3 must be [CALC]
    assert '<div class="metric-card-title"><span class="badge badge-calc">[CALC]</span> Baseline Deviation</div>' in content
    # Ensure there is NO [PRED] badge for Baseline Deviation
    assert '<span class="badge badge-pred">[PRED]</span> Baseline Deviation' not in content


def test_zero_hallucination_claim_absent_from_dashboard():
    """Verify 'Zero Hallucination' claim has been removed and replaced with 'PASSED'."""
    with open("dashboard/app.py", "r") as f:
        content = f.read()
    assert "Zero Hallucination" not in content
    assert "**Grounding Validation:** PASSED" in content


# =========================================================================
# 7. GROUNDING & SAFETY VALIDATION
# =========================================================================

def test_grounding_validation_passes_for_valid_context():
    """Verify validate_copilot_response passes for deterministic fallback prose."""
    ctx = context_builder.build_context("What is the factory energy consumption and how does it compare with baseline?")
    ans = generate_deterministic_fallback(ctx, "What is the factory energy consumption and how does it compare with baseline?")
    val = validate_copilot_response(ans, grounded_facts=ctx["grounded_facts"], context_text=ctx["text_representation"])
    assert val["is_valid"] is True
    assert len(val["violations"]) == 0


def test_grounding_rejects_forbidden_control_and_failure():
    """Verify forbidden failure predictions and control commands are rejected."""
    bad_ans_1 = "The motor will fail in 2 days. Shut down the machine immediately."
    val_1 = validate_copilot_response(bad_ans_1, grounded_facts=[], context_text="")
    assert val_1["is_valid"] is False
    assert any("failure" in v.lower() for v in val_1["violations"])
    assert any("control" in v.lower() for v in val_1["violations"])


# =========================================================================
# 8. API INTEGRATION INTEGRITY
# =========================================================================

def test_copilot_chat_api_general_chat_response(client):
    """Verify /copilot/chat returns GENERAL_CHAT intent and non-factory answer for 'What is my name?'."""
    res = client.post("/copilot/chat", json={"question": "What is my name?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "GENERAL_CHAT"
    assert "0.3962" not in data["answer"]
    assert "do not possess personal profile information" in data["answer"]


def test_copilot_chat_api_factory_summary_response(client):
    """Verify /copilot/chat returns FACTORY_SUMMARY intent and grounded factory metrics."""
    res = client.post("/copilot/chat", json={"question": "What is the factory energy consumption?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "FACTORY_SUMMARY"
    assert "kWh" in data["answer"]
    assert data["grounded"] is True


def test_copilot_chat_api_machine_response_matches_selected_machine(client):
    """Verify /copilot/machine/M01 returns M01 context."""
    res = client.post("/copilot/machine/M01", json={"question": "What is the energy status of this machine?"})
    assert res.status_code == 200
    data = res.json()
    assert "M01" in data["answer"]
    assert data["intent"] == "MACHINE_ANALYSIS"


def test_baseline_is_labeled_predicted_in_dashboard():
    """Verify Baseline is labeled [PRED] across dashboard cards."""
    with open("dashboard/app.py", "r") as f:
        content = f.read()
    assert '<div class="metric-card-title"><span class="badge badge-pred">[PRED]</span> Baseline</div>' in content


def test_factory_copilot_values_equal_demo_factory_endpoint(client):
    """Verify /copilot/summary returns factory energy metrics aligned with /demo/factory."""
    sum_res = client.get("/copilot/summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()

    fact_res = client.get("/demo/factory")
    assert fact_res.status_code == 200
    fact_data = fact_res.json()

    assert abs(sum_data["energy_kwh"] - fact_data["energy"]["actual_energy_kwh"]) < 1e-4
    assert abs(sum_data["expected_energy_kwh"] - fact_data["energy"]["expected_energy_kwh"]) < 1e-4
    assert sum_data["production_units"] == fact_data["production"]["total_units"]


def test_machine_copilot_values_equal_demo_machine_endpoint(client):
    """Verify /copilot/machine/M01 returns actual energy and state aligned with /demo/machine/M01."""
    cop_res = client.post("/copilot/machine/M01", json={"question": "What is the status of M01?"})
    assert cop_res.status_code == 200
    cop_data = cop_res.json()

    m_res = client.get("/demo/machine/M01")
    assert m_res.status_code == 200
    m_data = m_res.json()

    m_actual = m_data["actual_energy_kwh"]
    assert str(m_actual) in cop_data["answer"] or str(round(m_actual, 4)) in cop_data["answer"]


def test_legacy_copilot_query_endpoint(client):
    """Verify legacy /copilot/query route functions as a thin wrapper over the unified pipeline."""
    res = client.post("/copilot/query", json={"query": "What is machine learning?", "machine_id": "M01"})
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "response" in data
    assert data["grounded"] is True


def test_in_process_fallback_client_execution():
    """Verify get_fallback_client in dashboard can process endpoints locally."""
    from dashboard.app import get_fallback_client
    fb_client = get_fallback_client()
    res = fb_client.get("/demo/status")
    assert res.status_code == 200
    assert "current_scenario_phase" in res.json()
    assert "demo_mode" in res.json()

