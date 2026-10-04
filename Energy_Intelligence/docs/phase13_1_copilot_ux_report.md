# Phase 13.1 Copilot Behavior, Data Consistency & Dashboard UX Hardening Report

## Executive Summary
**Person 3 — Energy & Production Intelligence Engine**  
**Schneider Electric 2026 Smart Manufacturing Hackathon**  
**Baseline Test Count:** 250 passed (Phase 13) → 361 passed (Phase 13 hardening) → **370 passed, 0 failed** (Phase 13.1 complete).

Phase 13.1 was executed to resolve remaining Copilot behavior, data consistency, and dashboard user experience issues without rebuilding the core analytics engine, changing the machine learning baseline/forecasting models, or compromising Phase 12.1 mathematical reconciliation. The Copilot has been transformed from a generic report generator into a conversational, grounded industrial assistant while strictly enforcing that every numerical value presented to the operator or judge originates from the same authoritative demo analysis snapshot.

---

## 1. Problems Discovered
1. **Generic / Repeated Answers:** Certain queries produced canned capability lists rather than answering the user's specific operational question.
2. **"How this is working" Intent Routing:** "How does this system work?" or "how is this working" routed into general conversational fallback, returning capability bullet points instead of explaining the five-step engineering architecture.
3. **Intent Ambiguity:** Inquiries regarding baseline, comparison, SEC, and total factory energy shared overlapping intent branches and dumped identical full reports.
4. **Follow-Up Context Disconnect:** Short follow-ups ("Is that good?", "Why?", "What about M02?") failed to consistently resolve the antecedent machine or topic while retrieving authoritative metrics.
5. **Telemetry Snapshot Divergence:** Copilot and dashboard could compute metrics independently over slightly varying window representations.
6. **Duplicate Asset Selectors:** Machine selection existed in both the sidebar ("Inspect Asset") and Section 5 radio buttons ("Select Asset for Deep Telemetry Analysis").
7. **Cluttered Sidebar:** Developer-level metrics (raw telemetry counter, elapsed runtime, MQTT QoS connection parameters) dominated the primary navigation bar.
8. **Ambiguous Forecast Terminology:** The total 5-minute projected demand (~2.24 kWh) could be conflated with the per-minute interval rate (~0.448 kWh/min).
9. **Ambiguous Utilization Semantics:** Machine utilization was reported as a bare percentage without defining whether it represented productive time, calendar time, or electrical availability.
10. **Zero-Savings Misinterpretation:** When factory consumption operated below baseline, reporting "Potential Savings: ₹0.00" without explanation created the impression that the system was broken rather than acknowledging efficient below-baseline operation.
11. **Chat UI report-dumping:** Every answer rendered mandatory section headers (`Summary:`, `Evidence:`, `Interpretation:`, `Recommended Next Step:`), bloating the conversation history into a scrolling report.

---

## 2. Root Causes Identified
- **Uncoordinated Telemetry Slicing:** `ContextBuilder.build_context()` queried `telemetry_store` or `demo_state` independently of `GET /demo/factory`, allowing float precision or microsecond edge discrepancies.
- **Overly Broad Intent Fallthrough:** Regex matching in `classify_intent()` routed "how is this working" or "baseline" queries into broad catch-alls (`GENERAL_CHAT` or `FACTORY_SUMMARY`).
- **Duplicate Widget State in Streamlit:** Both `st.sidebar.selectbox` and `st.radio(key="deep_dive_asset_selector")` independently updated session state, causing UI desynchronization.
- **Rigid Legacy Response Templating:** `generate_deterministic_fallback()` defaulted to 4-part legacy headings for every query unless bypassed.
- **Unqualified UI Labels:** Metric cards lacked semantic qualifiers (e.g. "Total 5-Min" vs "Per-Minute Rate", "Productive Utilization").

---

## 3. Data Consistency Architecture
The system enforces a strict single-source-of-truth architecture:

```
                  Telemetry Ingestion
                           ↓
               Authoritative Demo State
                           ↓
             Deterministic Analytics Engine
                           ↓
             Shared Authoritative Snapshot
            ┌──────────────┴──────────────┐
            ▼                             ▼
   Streamlit Dashboard            Energy Copilot
   (Sections 1 to 10)           (API POST /copilot/chat)
            │                             │
            └──────────────┬──────────────┘
                           ▼
          Identical Timestamps, Energy, Baseline,
              Production, Deviation & SEC
```

### Authoritative Window Definition
Whenever the operator asks about "current energy", "current baseline", "current production", or "current SEC", "current" is deterministically interpreted as:
**The active contiguous analysis window of the authoritative demonstration state.**
- Start timestamp: ISO string matching `demo_state.get_active_demo_window()["start_time"]`.
- End timestamp: ISO string matching `demo_state.get_active_demo_window()["end_time"]`.
- `ContextBuilder` inspects `demo_state.get_active_demo_snapshot()` first before any recalculation.

---

## 4. Copilot Routing & Intent Classification Improvements
`classify_intent()` was refined into deterministic industrial routing:

| Intent Category | Trigger Query Examples | Response Behavior |
|:---|:---|:---|
| `HOW_IT_WORKS` | "How does this system work?", "how is this working", "explain how this works" | Returns 5-step engineering pipeline (telemetry → analytics → baseline → forecast → opportunities). |
| `GENERAL_CHAT` / `CAPABILITIES` | "What can you do?", "what can you analyze?", "capabilities" | Returns structured list of analytical capabilities and strict responsibility boundaries. |
| `BASELINE` | "What is the factory baseline?", "what is expected energy" | Returns direct baseline value ({expected_kwh} kWh), production output, and actual deviation. |
| `ENERGY_DEVIATION` | "Is the factory above or below baseline?", "compare with baseline" | Direct comparison: state whether factory is above/below, deviation kWh and %, and savings implications. |
| `SEC` / `EFFICIENCY` | "What is the factory SEC?", "can we calculate SEC right now?" | Normal SEC value if units > 0; explains mathematically undefined nature if units == 0. |
| `MACHINE_STATUS` | "What is M01 doing?", "is M01 running" | Direct concise operational state, active kW, and health score. |
| `MACHINE_ENERGY` | "How much energy did M01 consume?", "energy draw of M04" | Direct consumed kWh, baseline expected kWh, and deviation %. |
| `IDLE_ANALYSIS` | "How much energy is consumed during non-production?", "idle energy" | Unproductive idle allocation vs low-power sleep standby draw. |
| `OPPORTUNITIES` | "Which machine should I investigate first?", "top opportunity" | Top prioritized efficiency recommendation with supporting metric. |
| `FORECAST` | "What will energy consumption be over the next 5 minutes?" | 5-minute projection, distinguishing 5-min total from per-minute demand rate. |
| `SAVINGS` | "How much energy could we save?", "why is savings zero?" | Clear explanation of potential gross savings or efficient below-baseline operation. |
| `MACHINE_HEALTH_CONTEXT` | "What is the health of M04?", "vibration on M03" | Ingests Person 2 contextual signals with explicit responsibility boundary notice. |

---

## 5. Conversation Context & Multi-Turn Reference Resolution
- **Lightweight State Tracking:** The Copilot accepts a bounded history payload (last 8 turns).
- **Antecedent Reference Resolution:** When the user asks "Is that good?", "Is that above baseline?", or "Why?", the system resolves "that" to the machine ID or analytical metric from the preceding turn.
- **Grounding Integrity Maintained:** Context is used *strictly* to resolve entity references. Numerical facts are never retrieved from conversational memory; they are re-queried directly from the authoritative analytics engine.

---

## 6. Chat UI & Dashboard UX Hardening
1. **Streamlit Section 11 Form & History:**
   - User queries and assistant responses use high-contrast, visually distinct industrial cards (`#1E293B` vs `#0F172A`).
   - Chat history is enclosed in a bounded, internally scrollable container (`height=420`).
   - The query input box (`st.text_input` within `st.form`) remains fixed and always accessible at the bottom of the section.
   - Quick preset buttons and example chips populate the input draft without bypassing validation or grounding.
2. **Single Source of Truth for Asset Selection:**
   - Duplicate `st.radio` selector was completely removed from Section 5.
   - Asset inspection is controlled entirely from the sidebar Fleet Navigation selectbox (`All Factory Assets`, `M01`, `M02`, `M03`, `M04`).
   - When "All Factory Assets" is selected, Section 5 deterministically defaults to asset `M01` with clear advisory text.
3. **Sidebar Reorganization:**
   - Top: High-level System Status (Backend Connected, Database Connected, Telemetry Active).
   - Middle: Demonstration Controls (Run Demo, Reset Demo, Refresh Data) and Demo Scenario Badge (`PHASE_A_NORMAL`).
   - Navigation: Fleet Navigation dropdown.
   - Diagnostics: Raw telemetry counters, elapsed runtime, and MQTT parameters moved into a clean collapsible expander `⚙️ System Diagnostics`.
4. **Forecast Terminology:**
   - Dashboard Section 8 explicitly distinguishes total 5-minute demand from the per-minute interval rate using prominent metric tiles:
     - `FORECASTED ENERGY — NEXT 5 MINUTES`: 2.2417 kWh (Total 5-min)
     - `AVERAGE DEMAND RATE`: ~0.4483 kWh/min
     - Chart Title: `Forward Interval 1–5: Projected Energy per 1-Minute Interval`
5. **Productive Utilization Definition:**
   - Machine utilization in Section 5 is explicitly labeled `Productive Utilization`.
   - Tooltip text states: *"Calculated over the authoritative analysis window as (Productive Time [RUNNING, DEGRADED, OVERLOAD] / Total Observed Time) * 100."*
6. **Zero-Savings Presentation:**
   - When actual consumption operates below baseline, Section 9 and Copilot state:
     *"No above-baseline energy savings opportunity was detected in this window because actual consumption is already below the production-aware baseline. Potential gross savings: 0.0000 kWh (₹0.00)."*

---

## 7. Test Results & Verification
- **Full Pytest Suite:** 370 tests collected, **370 passed, 0 failed** in 74.31s.
- **Phase 13.1 Specific UX Test Suite (`test_phase13_1_copilot_ux.py`):** 39 passed in 7.85s.

### Specific Verification Items Passed:
1. Current factory question uses authoritative demo window.
2. Copilot and dashboard actual energy values match exactly.
3. Copilot and dashboard baseline values match exactly.
4. Copilot and dashboard production counts match exactly.
5. Copilot and dashboard SEC values match exactly.
6. "How does this system work?" routes to `HOW_IT_WORKS` and details the 5-step pipeline.
7. "What can you do?" routes to capability breakdown without report headers.
8. "What is the factory baseline?" returns a direct, baseline-focused response.
9. Factory energy question does not dump unnecessary full 4-part report headers.
10. Follow-up machine question resolves machine context.
11. Follow-up "Is that good?" / "Is that above baseline?" resolves previous machine/topic.
12. Follow-up queries remain grounded in authoritative analytics.
13. Quick preset queries route through the normal `/copilot/chat` pipeline.
14. Duplicate machine selector removed from Section 5.
15. Forecast total (5-min) and per-minute rate terminology are explicit and unambiguous.
16. Productive utilization is explicitly labeled with formal definition tooltip.
17. Zero-savings condition is clearly explained when actual <= baseline.
18. Person 1 machine control commands are strictly forbidden and rejected.
19. Person 2 mechanical fault diagnoses are strictly forbidden and rejected.
20. Unsupported numbers trigger grounding rejection and regeneration/fallback.
21. Offline Ollama fallback produces deterministic, accurate responses.
22. Chat history container does not push input form out of view.
23. Demo reset cleanly resets demo buffer without leaking stale state.
24. Machine selection updates Copilot context appropriately.
25. "All Factory Assets" defaults cleanly without creating stale machine context.

---

## 8. Manual Test Matrix Execution Summary
All 24 test matrix scenarios were executed against the running FastAPI test client via `scripts/verify_manual_matrix.py`:
- **GENERAL:** "How does this system work?" → 5-step engineering pipeline; "What can you do?" → Capabilities & boundaries; "Hello" → Industrial assistant greeting.
- **FACTORY:** Energy, Production, Baseline, Comparison, and SEC queries all matched the exact authoritative numbers (0.3962 kWh actual, 0.7923 kWh baseline, 3 units produced, 0.1321 kWh/unit SEC).
- **MACHINE:** M01 status ("SLEEP at 0.36 kW"), M04 energy ("0.0921 kWh"), and M04 utilization were verified.
- **ENERGY:** Non-production idle energy (0.0076 kWh on M01) and top opportunity (M01 idle reduction) correctly identified.
- **FORECAST:** Multi-step 5-minute projection (2.2417 kWh) correctly explained.
- **SAVINGS:** Zero savings explained as operating below baseline tolerances (₹0.00 / 0.0000 kWh).
- **FOLLOW-UP:** "Is that above baseline?" and "What about M02?" correctly maintained entity references while pulling authoritative metrics.

---

## 9. Remaining Architectural Boundaries
- **Person 1 Boundary:** Copilot suggests energy investigations; it never issues PLC, actuator, or motor speed commands.
- **Person 2 Boundary:** Copilot reads vibration, temperature, and anomaly scores as advisory context; it never diagnoses mechanical bearing or winding faults.
- **Model Inference:** When Ollama is available, Qwen3 provides natural explanations with strict grounding validation; when offline, deterministic Python fallback guarantees 100% availability.
