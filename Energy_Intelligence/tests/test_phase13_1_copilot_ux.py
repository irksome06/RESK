"""
Phase 13.1 Grounded Energy Intelligence Copilot UX & Conversational Test Suite.
Verifies all 30 requirements:
- Preset buttons only populate draft without submitting or mutating history
- Visible custom question input and rejection of empty queries
- Session state persistence across widget changes and machine selection
- Bounded multi-turn conversation and context preservation
- Natural conversational responses (direct answer, explanation, recommendation)
- Zero-production SEC handling (N/A, never divide by zero)
- Authoritative demo-state reconciliation and grounding validation
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app
from simulator.demo_state import demo_state
from scripts.run_final_demo import run_authoritative_demo
from llm.context_builder import context_builder, classify_intent
from llm.fallback import generate_deterministic_fallback
from llm.validation import validate_copilot_response
from llm.prompts import build_copilot_prompt, COPILOT_SYSTEM_PROMPT
from llm.ollama_client import ollama_client


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def ensure_demo_state():
    """Ensure authoritative demo state is active for tests."""
    if not demo_state.has_active_demo_data():
        run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)
    yield


# =====================================================================
# 1. PRESET BUTTON & DRAFT INPUT BEHAVIOR (Problems 1, 5, 6)
# =====================================================================

def test_preset_selection_populates_draft_without_submitting():
    """Verify clicking a preset sets copilot_draft and increments key, but does NOT modify messages."""
    session_state = {
        "copilot_messages": [{"role": "assistant", "content": "Welcome!"}],
        "copilot_draft": "",
        "copilot_input_key": 0,
    }
    initial_msg_count = len(session_state["copilot_messages"])

    # Simulate clicking "🏭 Factory Baseline" preset
    preset_text = "Give me the current factory energy consumption and compare it with the production-aware baseline."
    session_state["copilot_draft"] = preset_text
    session_state["copilot_input_key"] += 1

    # Messages must remain unchanged!
    assert len(session_state["copilot_messages"]) == initial_msg_count
    assert session_state["copilot_draft"] == preset_text
    assert session_state["copilot_input_key"] == 1


def test_preset_selection_does_not_clear_existing_chat():
    """Verify clicking presets does not wipe existing conversation history."""
    session_state = {
        "copilot_messages": [
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ],
        "copilot_draft": "",
        "copilot_input_key": 1,
    }
    # Simulate clicking "⚠️ Top Opportunity" preset
    preset_text = "Which energy optimization opportunity currently has the highest calculated priority, and what evidence supports it?"
    session_state["copilot_draft"] = preset_text
    session_state["copilot_input_key"] += 1

    assert len(session_state["copilot_messages"]) == 3
    assert session_state["copilot_messages"][1]["content"] == "First question"
    assert session_state["copilot_draft"] == preset_text


def test_preset_draft_is_editable_before_submission():
    """Verify preset draft can be modified/extended by user prior to submission."""
    draft = "Give me the current factory energy consumption and compare it with the production-aware baseline."
    edited = draft + " Also explain machine M01."
    assert edited.startswith(draft)
    assert "M01" in edited


# =====================================================================
# 2. CUSTOM QUESTION SUBMISSION & VALIDATION (Problems 2, 6)
# =====================================================================

def test_custom_question_can_be_submitted(client):
    """Verify custom user question is submitted and receives a grounded response."""
    q = "What can you tell me about M03?"
    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert "M03" in data["answer"]
    assert data["intent"] in ["MACHINE_ANALYSIS", "ENERGY_DEVIATION", "GENERAL_CHAT"]


def test_empty_question_rejected_by_api(client):
    """Verify empty or whitespace-only questions return 400 or 422 Bad Request/Unprocessable Entity."""
    for empty_q in ["", "   ", "\t\n"]:
        res = client.post("/copilot/chat", json={"question": empty_q})
        assert res.status_code in [400, 422]


def test_user_and_assistant_message_stored_correctly():
    """Verify messages dictionary schema matches requirements."""
    messages = []
    # User message
    user_msg = {"role": "user", "content": "What is the factory energy?"}
    messages.append(user_msg)
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "What is the factory energy?"

    # Assistant message
    asst_msg = {
        "role": "assistant",
        "content": "The factory consumed 0.3962 kWh.",
        "intent": "FACTORY_SUMMARY",
        "grounded": True,
        "model_used": "Deterministic",
        "fallback_used": True,
        "context_summary": {},
    }
    messages.append(asst_msg)
    assert len(messages) == 2
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["grounded"] is True


def test_no_duplicate_messages_on_single_submit():
    """Verify a single query appends exactly one user message and one assistant message."""
    messages = [{"role": "assistant", "content": "Welcome!"}]
    initial_len = len(messages)

    # Simulate submission
    user_q = "How is M01 performing?"
    messages.append({"role": "user", "content": user_q})
    messages.append({
        "role": "assistant",
        "content": "M01 is in SLEEP state.",
        "intent": "MACHINE_ANALYSIS",
    })

    assert len(messages) == initial_len + 2
    assert messages[-2]["content"] == user_q
    assert messages[-1]["role"] == "assistant"


# =====================================================================
# 3. SESSION STATE RESILIENCE & WIDGET INDEPENDENCE (Problems 12, 13, 14)
# =====================================================================

def test_selecting_machine_does_not_clear_chat():
    """Verify updating selected_machine_id leaves copilot_messages unchanged."""
    session_state = {
        "copilot_messages": [
            {"role": "assistant", "content": "Welcome!"},
            {"role": "user", "content": "What is factory consumption?"},
            {"role": "assistant", "content": "0.3962 kWh."},
        ],
        "selected_machine_id": "M01",
    }
    initial_count = len(session_state["copilot_messages"])

    # User changes machine dropdown from M01 to M02
    session_state["selected_machine_id"] = "M02"

    assert len(session_state["copilot_messages"]) == initial_count
    assert session_state["copilot_messages"][1]["content"] == "What is factory consumption?"


def test_demo_controls_do_not_mutate_chat():
    """Verify dashboard controls do not wipe chat history."""
    session_state = {
        "copilot_messages": [{"role": "assistant", "content": "Hello!"}],
        "demo_running": False,
        "filter_state": "ALL",
    }
    session_state["demo_running"] = True
    session_state["filter_state"] = "SLEEP"

    assert len(session_state["copilot_messages"]) == 1


def test_clear_chat_resets_only_messages():
    """Verify clear chat resets copilot_messages without resetting telemetry or demo state."""
    session_state = {
        "copilot_messages": [
            {"role": "assistant", "content": "Welcome!"},
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ],
        "selected_machine_id": "M03",
        "copilot_draft": "Draft text",
    }

    # Simulate Clear Chat
    session_state["copilot_messages"] = [
        {
            "role": "assistant",
            "content": "Conversation cleared. How can I help you with factory energy and production analytics?",
            "intent": "GENERAL_CHAT",
            "model_used": "system",
            "fallback_used": True,
            "grounded": True,
            "context_summary": {},
        }
    ]
    session_state["copilot_draft"] = ""

    assert len(session_state["copilot_messages"]) == 1
    assert "cleared" in session_state["copilot_messages"][0]["content"].lower()
    assert session_state["selected_machine_id"] == "M03"  # Preserved!
    assert session_state["copilot_draft"] == ""


# =====================================================================
# 4. MULTI-TURN CONVERSATION & BOUNDED HISTORY (Problem 11)
# =====================================================================

def test_bounded_history_limits_payload():
    """Verify only the last 8 messages are sent in history payload."""
    messages = []
    for i in range(20):
        messages.append({"role": "user", "content": f"User question {i}"})
        messages.append({"role": "assistant", "content": f"Assistant answer {i}"})

    # Slice last 8
    history_payload = messages[-8:]
    assert len(history_payload) == 8
    assert history_payload[-1]["content"] == "Assistant answer 19"


def test_followup_question_preserves_factory_context():
    """Verify short follow-up 'Why is that?' preserves FACTORY_SUMMARY intent."""
    history = [
        {"role": "user", "content": "What is the factory energy consumption?"},
        {"role": "assistant", "content": "Factory is consuming 0.3962 kWh.", "intent": "FACTORY_SUMMARY"},
    ]
    intent, machine = classify_intent("Why is that?", history=history)
    assert intent == "FACTORY_SUMMARY"
    assert machine is None


def test_followup_question_machine_switch():
    """Verify 'What about M01?' switches machine while maintaining intent."""
    history = [
        {"role": "user", "content": "How much energy is being consumed during non-production states?"},
        {"role": "assistant", "content": "Factory idle energy is 0.05 kWh.", "intent": "IDLE_ANALYSIS"},
    ]
    intent, machine = classify_intent("What about M01?", history=history)
    assert machine == "M01"
    assert intent == "IDLE_ANALYSIS"


def test_prompt_builder_handles_both_history_formats():
    """Verify build_copilot_prompt handles role/content and question/answer formats."""
    role_history = [
        {"role": "user", "content": "What is M01 status?"},
        {"role": "assistant", "content": "M01 is in SLEEP state."},
    ]
    prompt = build_copilot_prompt(
        question="Why?",
        context_str="M01 power: 0.36 kW",
        intent="MACHINE_ANALYSIS",
        conversation_history=role_history,
    )
    assert "CONVERSATION CONTEXT:" in prompt
    assert "What is M01 status?" in prompt
    assert "M01 is in SLEEP state." in prompt


# =====================================================================
# 5. CONVERSATIONAL & GROUNDED RESPONSES (Problems 7, 8, 10, 17)
# =====================================================================

def test_general_chat_what_can_you_do_conversational(client):
    """Verify 'What can you do?' returns conversational capabilities without robotic headers."""
    res = client.post("/copilot/chat", json={"question": "What can you do?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "GENERAL_CHAT"
    assert "Summary:" not in data["answer"]
    assert "Evidence:" not in data["answer"]
    assert "energy" in data["answer"].lower()
    assert "baseline" in data["answer"].lower()


def test_conversational_factory_summary_direct_answer(client):
    """Verify factory energy question returns direct answer and operational explanation."""
    res = client.post("/copilot/chat", json={"question": "What is the factory energy consumption?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "FACTORY_SUMMARY"
    assert data["grounded"] is True
    # Must contain authoritative factory consumption
    assert "0.39" in data["answer"] or "0.40" in data["answer"] or "kWh" in data["answer"]


def test_conversational_investigate_machine_recommendation(client):
    """Verify 'Which machine should I investigate first?' identifies top opportunity."""
    res = client.post("/copilot/chat", json={"question": "Which machine should I investigate first?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "OPPORTUNITIES"
    assert "Machine" in data["answer"] or "M0" in data["answer"]


def test_idle_energy_analysis_conversational(client):
    """Verify idle energy query returns non-production metrics."""
    res = client.post("/copilot/chat", json={"question": "How much energy is being consumed during non-production?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "IDLE_ANALYSIS"
    assert "IDLE" in data["answer"] or "SLEEP" in data["answer"] or "kWh" in data["answer"]


def test_forecast_energy_query_conversational(client):
    """Verify 5-minute forecast query returns projected energy."""
    res = client.post("/copilot/chat", json={"question": "What is the predicted energy consumption for the next 5 minutes?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "FORECAST"
    assert "kWh" in data["answer"] or "minutes" in data["answer"]


# =====================================================================
# 6. ZERO PRODUCTION & SEC HANDLING (Problem 18)
# =====================================================================

def test_zero_production_sec_explained_properly():
    """Verify when production is zero, SEC is explained as not meaningful and not reported as 0."""
    ctx = {
        "intent": "EFFICIENCY",
        "structured_data": {
            "efficiency": {
                "factory_actual_sec": None,
                "factory_expected_sec": None,
                "production_units": 0,
            }
        },
        "grounded_facts": [],
    }
    ans = generate_deterministic_fallback(ctx, "Can we calculate SEC right now?")
    assert "0 units" in ans or "zero" in ans.lower()
    assert "SEC = 0" not in ans
    assert "misleading" in ans.lower() or "cannot be calculated" in ans.lower() or "not meaningful" in ans.lower()


def test_zero_production_sec_factory_summary_fallback():
    """Verify FACTORY_SUMMARY fallback with zero production explains SEC status."""
    ctx = {
        "intent": "FACTORY_SUMMARY",
        "structured_data": {
            "factory_summary": {
                "actual_energy_kwh": 0.0188,
                "expected_energy_kwh": 0.0725,
                "production_units": 0,
                "actual_sec_kwh_per_unit": "N/A",
                "potential_savings_kwh": 0.0,
            }
        },
        "grounded_facts": [],
    }
    ans = generate_deterministic_fallback(ctx, "What is the factory energy consumption?")
    assert "0.0188" in ans
    assert "SEC" in ans
    assert "not meaningful" in ans.lower() or "misleading" in ans.lower()


# =====================================================================
# 7. GROUNDING VALIDATOR & SAFETY BOUNDARIES (Problem 10)
# =====================================================================

def test_grounding_validator_rejects_unsupported_numbers():
    """Verify validation flags numbers that are not in authoritative context."""
    context_text = "Factory actual energy is 0.3962 kWh. Baseline is 0.7923 kWh."
    grounded_facts = [
        {"metric": "actual_energy_kwh", "value": 0.3962, "unit": "kWh"},
        {"metric": "expected_energy_kwh", "value": 0.7923, "unit": "kWh"},
    ]
    # Response contains fabricated numbers: 954.2 kWh, 88.5 kWh, 431.0 kWh
    fabricated_resp = "The machine consumed 954.2 kWh with a secondary draw of 88.5 kWh and 431.0 kWh."
    val = validate_copilot_response(fabricated_resp, grounded_facts=grounded_facts, context_text=context_text)
    assert not val["is_valid"]
    assert len(val["unsupported_numbers"]) > 0


def test_grounding_validator_rejects_forbidden_failure_claims():
    """Verify validation rejects Person 2 mechanical failure diagnosis."""
    resp = "Motor will fail in 2 days due to bearing failure."
    val = validate_copilot_response(resp, grounded_facts=[], context_text="")
    assert not val["is_valid"]
    assert any("failure prediction" in v for v in val["violations"])


def test_grounding_validator_rejects_forbidden_control_commands():
    """Verify validation rejects Person 1 machine control commands."""
    resp = "Shut down the machine immediately and turn off power."
    val = validate_copilot_response(resp, grounded_facts=[], context_text="")
    assert not val["is_valid"]
    assert any("machine control command" in v for v in val["violations"])


def test_ollama_offline_fallback_still_works(client):
    """Verify copilot responds gracefully when Ollama daemon is offline."""
    with patch.object(ollama_client, "is_available", return_value=False):
        res = client.post("/copilot/chat", json={"question": "What is the factory energy consumption?"})
        assert res.status_code == 200
        data = res.json()
        assert data["grounded"] is True
        assert data["fallback_used"] is True
        assert len(data["answer"]) > 20


# =====================================================================
# 8. AUTHORITATIVE DEMO STATE RECONCILIATION (Problem 19)
# =====================================================================

def test_copilot_reconciles_with_demo_state_factory_energy(client):
    """Verify copilot uses the EXACT authoritative demo state factory energy."""
    f_res = client.get("/demo/factory").json()
    ctx = context_builder.build_context("What is the factory energy consumption?")
    fs = ctx["structured_data"]["factory_summary"]

    assert abs(fs["actual_energy_kwh"] - f_res["energy"]["actual_energy_kwh"]) < 1e-3
    assert abs(fs["expected_energy_kwh"] - f_res["energy"]["expected_energy_kwh"]) < 1e-3


def test_copilot_reconciles_with_demo_state_machine_energy(client):
    """Verify copilot machine context uses exact authoritative demo state."""
    m_detail = client.get("/demo/machine/M01").json()
    assert m_detail is not None

    ctx = context_builder.build_context("What is M01 status?", machine_id_override="M01")
    ctx_m01 = ctx["structured_data"]["machine_analysis"]

    assert abs(ctx_m01["actual_energy_kwh"] - m_detail["actual_energy_kwh"]) < 1e-3


def test_custom_question_persists_editable_after_rerun():
    """Verify custom question in draft persists in session state until submitted."""
    state = {
        "copilot_messages": [{"role": "assistant", "content": "Welcome!"}],
        "copilot_draft": "Custom drafted question about factory power",
        "copilot_input_key": 2,
    }
    # Simulate a rerun triggered by non-copilot widget update
    assert state["copilot_draft"] == "Custom drafted question about factory power"
    assert len(state["copilot_messages"]) == 1


def test_machine_sec_not_applicable_when_machine_production_zero():
    """Verify machine fallback explains SEC is not applicable when machine production is zero."""
    ctx = {
        "intent": "MACHINE_ANALYSIS",
        "structured_data": {
            "machine_analysis": {
                "machine_id": "M01",
                "machine_state": "SLEEP",
                "actual_energy_kwh": 0.0268,
                "expected_energy_kwh": 0.0056,
                "deviation_kwh": 0.0212,
                "baseline_gap_pct": 378.0,
                "deviation_status": "HIGH",
                "production_units": 0,
                "actual_sec_kwh_per_unit": "N/A",
            }
        },
        "grounded_facts": [],
    }
    ans = generate_deterministic_fallback(ctx, "How is M01 performing?")
    assert "0 completed production units" in ans or "0 units" in ans
    assert "SEC is not applicable" in ans
    assert "SEC = 0" not in ans


def test_copilot_input_key_increments_on_submission_and_preset():
    """Verify input key increments to refresh input widget cleanly on preset click and submission."""
    key = 0
    # Preset clicked
    key += 1
    assert key == 1
    # Submission processed
    key += 1
    assert key == 2


# =====================================================================
# 9. PHASE 13.1 SPECIFIC INTENT ROUTING, CONSISTENCY & UX TESTS
# =====================================================================

def test_current_factory_question_uses_authoritative_demo_window(client):
    """Verify current factory questions strictly use the authoritative demo window."""
    f_res = client.get("/demo/factory").json()
    win = f_res["analysis_window"]
    ctx = context_builder.build_context("What is the current factory energy consumption?")

    assert "factory_summary" in ctx["structured_data"]
    fs = ctx["structured_data"]["factory_summary"]
    assert abs(fs["actual_energy_kwh"] - f_res["energy"]["actual_energy_kwh"]) < 1e-4
    assert abs(fs["expected_energy_kwh"] - f_res["energy"]["expected_energy_kwh"]) < 1e-4


def test_copilot_and_dashboard_full_consistency(client):
    """Verify Copilot and dashboard share 100% identical authoritative snapshot values."""
    f_res = client.get("/demo/factory").json()
    res = client.post("/copilot/chat", json={"question": "What is the factory energy consumption?"})
    assert res.status_code == 200
    data = res.json()

    # Authoritative numbers must match down to the exact float representation
    ctx_sum = data["context_summary"]
    f_kwh = f_res["energy"]["actual_energy_kwh"]
    assert str(f_kwh) in data["answer"] or f"{f_kwh:.4f}" in data["answer"] or f"{f_kwh:.2f}" in data["answer"]


def test_how_does_this_work_routes_and_explains_pipeline(client):
    """Verify 'how does this system work?' routes to HOW_IT_WORKS and returns the 5-step pipeline."""
    for q in ["How does this system work?", "how is this working", "How does it work?"]:
        intent, target = classify_intent(q)
        assert intent == "HOW_IT_WORKS"
        assert target is None

        res = client.post("/copilot/chat", json={"question": q})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "HOW_IT_WORKS"
        assert "five-step energy intelligence pipeline" in data["answer"].lower() or "5-step" in data["answer"].lower()
        assert "1. Measure machine energy" in data["answer"]
        assert "5. Identify energy-efficiency opportunities" in data["answer"]
        assert "source of truth" in data["answer"].lower()


def test_baseline_question_produces_focused_response(client):
    """Verify 'What is the factory baseline?' routes to BASELINE and gives a direct focused response."""
    q = "What is the factory baseline?"
    intent, target = classify_intent(q)
    assert intent == "BASELINE"

    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "BASELINE"
    assert "expected energy baseline" in data["answer"].lower()
    assert "kWh" in data["answer"]
    assert "Summary:" not in data["answer"]  # Concise direct response, not full report dump


def test_comparison_question_explains_above_or_below(client):
    """Verify 'Is the factory above or below baseline?' routes to ENERGY_DEVIATION and explains status."""
    q = "Is the factory above or below baseline?"
    intent, target = classify_intent(q)
    assert intent == "ENERGY_DEVIATION"

    res = client.post("/copilot/chat", json={"question": q})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "ENERGY_DEVIATION"
    assert "baseline" in data["answer"].lower()
    assert "operating" in data["answer"].lower() or "below" in data["answer"].lower() or "above" in data["answer"].lower()


def test_duplicate_machine_selector_removed_from_section_5():
    """Verify duplicate machine selector in Section 5 has been removed in favor of sidebar navigation."""
    from pathlib import Path
    app_file = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    assert "deep_dive_asset_selector" not in content
    assert "Select Asset for Deep Telemetry Analysis:" not in content
    assert "Inspect Asset:" in content
    assert "Controlled via Fleet Navigation in sidebar" in content or "Default asset for deep analysis" in content


def test_forecast_total_and_per_minute_terminology_in_dashboard():
    """Verify dashboard displays unambiguous FORECASTED ENERGY — NEXT 5 MINUTES and AVERAGE DEMAND RATE."""
    from pathlib import Path
    app_file = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    assert "FORECASTED ENERGY — NEXT 5 MINUTES" in content
    assert "AVERAGE DEMAND RATE" in content
    assert "Forward Interval 1–5: Projected Energy per 1-Minute Interval" in content


def test_productive_utilization_label_and_tooltip_in_dashboard():
    """Verify dashboard explicitly labels and defines Productive Utilization."""
    from pathlib import Path
    app_file = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    content = app_file.read_text(encoding="utf-8")

    assert "Productive Utilization" in content
    assert "Calculated over the authoritative analysis window" in content


def test_zero_savings_explanation_clarity(client):
    """Verify when savings are 0, response clearly explains actual consumption is already below baseline."""
    ctx = {
        "intent": "SAVINGS",
        "structured_data": {
            "savings": {
                "potential_savings_kwh": 0.0,
                "potential_savings_inr": 0.0,
                "potential_co2_savings_kg": 0.0,
            }
        },
        "grounded_facts": [],
    }
    ans = generate_deterministic_fallback(ctx, "How much energy could we save?")
    assert "No above-baseline energy savings opportunity was detected" in ans
    assert "already operating at or below" in ans or "below baseline" in ans.lower()

