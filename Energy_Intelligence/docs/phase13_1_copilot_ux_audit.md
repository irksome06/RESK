# Phase 13.1 Grounded Energy Intelligence Copilot & Dashboard UX Audit

## Executive Summary
This document provides an evidence-based audit of Person 3's subsystem (Energy & Production Intelligence Engine) for the Schneider Electric 2026 Smart Manufacturing Hackathon.
Prior to this hardening pass, the platform passed 250 tests in Phase 13 (and 361 tests across Phase 13/Phase 13.1 test suites). However, manual review revealed conversational limitations, intent ambiguity, machine selector duplication, and UX rough edges that prevent the Copilot from behaving like a true conversational industrial assistant.

---

## 1. Current Copilot Flow & Architecture

The current pipeline operates as:
```
Simulator / Physical Sensors
        ↓
Canonical Telemetry (JSON over MQTT QoS 1)
        ↓
FastAPI Backend & SQLAlchemy / SQLite Store
        ↓
Deterministic Python Analytics Engine
        ↓
Authoritative Demo State (demo_state contiguous window)
        ↓
Context Builder (targeted structured JSON + grounded facts)
        ↓
Ollama / Qwen3 1.7B (or Deterministic Analytics Fallback)
        ↓
Hallucination & Safety Boundary Validator
        ↓
Streamlit Dashboard (Section 11)
```

### Flow Walkthrough
1. **User Query**: User submits a question in Section 11 of the Streamlit dashboard (`dashboard/app.py`).
2. **Intent Classification**: Sent via `POST /copilot/chat` to `api/copilot.py`, which delegates to `ContextBuilder.build_context(question, machine_id_override, history)` in `llm/context_builder.py`.
3. **Context Construction**: `classify_intent` selects an intent from regex/keyword heuristics. Authoritative metrics are gathered from `demo_state` or `telemetry_store`.
4. **Model Invocation & Validation**: `_process_copilot_query()` checks `ollama_client.is_available()`. If online, Qwen3 receives the prompt and system prompt; output is validated with `validate_copilot_response()`. If validation fails, regeneration is attempted once; if still invalid or Ollama is offline, `generate_deterministic_fallback()` generates the answer.
5. **Dashboard Rendering**: Stored in `st.session_state["copilot_messages"]` and displayed in the Section 11 container.

---

## 2. Current Intent Routing & Weaknesses

### Current Heuristic Routing in `llm/context_builder.py`:
- `classify_intent` uses regex and keyword matching.
- **Problem A: "How it works" vs "Capabilities"**:
  Queries such as "how this is working" or "how does this system work?" match general phrases and fall into `GENERAL_CHAT`, producing a generic capability list ("I can help you understand...") rather than explaining the 5-step engineering architecture.
- **Problem B: Ambiguity between Baseline, Comparison, and Summary**:
  Questions like "What is the factory baseline?" or "Is the factory above or below baseline?" or "What is factory consumption?" often route broadly to `FACTORY_SUMMARY` or `ENERGY_DEVIATION` with overlapping context dumps.
- **Problem C: Machine Status vs Machine Energy vs Health**:
  "What is M01 doing?" and "How much energy is M04 consuming?" both map to `MACHINE_ANALYSIS` without emphasizing operational state vs electrical draw.
- **Problem D: Follow-up Reference Resolution**:
  Questions like "Is that good?" or "Why?" need explicit reference tracking to preserve the previous subject (factory or specific machine) without losing the authoritative analytics grounding.

---

## 3. Data Consistency & Demo-State Flow

### How Dashboard Values Are Generated
- `dashboard/app.py` queries `GET /demo/factory` and `GET /demo/machine/{machine_id}`.
- `api/demo.py` loads records from `demo_state.get_demo_records()` and computes:
  - `total_actual_energy` via `compute_machine_savings`
  - `total_expected_energy` via `compute_machine_savings`
  - `factory_sec` via `calculate_factory_sec`
  - `deviation_kwh = total_actual_energy - total_expected_energy`
  - `potential_savings_kwh = max(0.0, deviation_kwh)`
  - Stores this result via `demo_state.set_active_demo_snapshot(snapshot.model_dump())`.

### How Copilot Values Are Generated
- `llm/context_builder.py` calls `demo_state.get_demo_records_dict()` and runs `compute_factory_efficiency`.
- **Identified Gap**: If Copilot recomputes metrics independently rather than prioritizing the shared `demo_state.get_active_demo_snapshot()`, slight floating-point differences or timestamp bounds could theoretically diverge.
- **Fix**: Copilot must reference the shared authoritative snapshot directly when active. "Current" must explicitly mean the authoritative analysis window of the demo run.

---

## 4. Identified Duplication & Dashboard UX Issues

| Issue ID | Area | Current Implementation | Root Cause | Impact |
|:---|:---|:---|:---|:---|
| **UX-01** | Asset Selection | Machine selector in Sidebar (`Inspect Asset`) AND Section 5 (`Select Asset for Deep Telemetry Analysis`). | Duplicate widget declarations with divergent default state. | User can select M01 in sidebar and M03 in Section 5, creating confusing multi-state navigation. |
| **UX-02** | Sidebar Clutter | Sidebar displays raw technical details: `Backend Mode`, `Telemetry Count`, `Elapsed Time`, `Database: Fallback SQLite`, `MQTT Ingestion: In-Process Loop`. | Developer/debug metrics exposed at top-level. | Cluttered judge experience; obscures core demo controls and fleet navigation. |
| **UX-03** | Forecast Semantics | Dashboard displays `Projected Energy Consumption — Next 5 Minutes: 2.2417 kWh` alongside 1-minute steps (~0.448 kWh). | Ambiguity between total 5-min cumulative projection and per-minute consumption. | Operator or judge might mistake 2.24 kWh as a 1-minute rate. |
| **UX-04** | Utilization Meaning | Machine metric displays `Utilization: 100.0%` without explanation. | No tooltip or definition of formula. | Unclear whether this is production capacity, electrical uptime, or operating state duration. |
| **UX-05** | Zero Savings Presentation | When actual energy < baseline, displays `Potential Savings: 0.0000 kWh (₹0.00)` with generic delta caption. | Lacks clear explanation of why savings are zero in this window. | Might imply optimization algorithms are inactive or ineffective. |
| **UX-06** | Copilot Chat Style | Analytical answers sometimes default to rigid section blocks (`Summary:`, `Evidence:`, `Interpretation:`, `Recommended Next Step:`). | Prompts and fallback generator formatted answers into static report templates. | Feels like a static batch report rather than an agile, conversational industrial assistant. |

---

## 5. Planned Fixes & Architectural Plan

1. **Deterministic Intent Expansion in `llm/context_builder.py`**:
   - `HOW_IT_WORKS`: Explains the 5-step pipeline (Measure → Compute SEC/State → Production-Aware Baseline → Forecast & Deviation → Prioritized Opportunities).
   - `CAPABILITIES`: Explicit list of analytical capabilities and boundaries (no direct control, no mechanical failure diagnosis).
   - `BASELINE`: Dedicated explanation of expected energy baseline model.
   - `COMPARISON`: Focuses on deviation percentage and above/below status.
   - `SEC`: Explains Specific Energy Consumption, zero-production handling, and unit normalization.
   - `MACHINE_STATUS` & `MACHINE_ENERGY`: Distinguishes state/health from kWh consumption.

2. **Absolute Snapshot Synchronization**:
   - `context_builder.py` references `demo_state.get_active_demo_snapshot()` as primary source of truth.
   - "Current" is strictly defined as the active demo window.

3. **Single Fleet Navigation Control in Dashboard**:
   - Remove radio button selector in Section 5.
   - Sidebar `Inspect Asset` selectbox is the sole source of truth; Section 5 automatically displays the selected asset (or default M01 when "All Factory Assets" is chosen).

4. **Streamlined Judge-Facing Sidebar**:
   - Clean top-level: System Status indicators, Demo Controls (`Run Demo`, `Reset Demo`, `Refresh Data`), Demo Scenario badge, and Fleet Navigation.
   - Technical diagnostics (`telemetry count`, `elapsed seconds`, `transport details`) collapsed into `⚙ System Diagnostics` expander.

5. **Clarified Forecast & Utilization Labels**:
   - Forecast: Explicitly separates Total 5-minute projected energy from Average per-minute rate.
   - Utilization: Labeled **Productive Utilization** with explicit formula tooltip: `(Productive Time [RUNNING, DEGRADED, OVERLOAD] / Total Observed Time) * 100`.

6. **Enhanced Zero-Savings Explanation**:
   - Explains that actual consumption is operating below expected baseline in the active window, meaning no gross above-baseline opportunity exists in this snapshot.
