# PHASE 13.1 — COMPREHENSIVE ARCHITECTURAL, UX & STATE AUDIT

**Project:** Person 3 — Energy & Production Intelligence Engine  
**Challenge:** Smart Manufacturing — Industrial Energy & Process Efficiency  
**Hackathon:** Schneider Electric 2026 Smart Manufacturing Hackathon  
**Phase:** 13.1 Hardening & UX/Consistency Refinement  
**Date:** October 2026  
**Auditor:** Senior Software Architect, Industrial Analytics & UX Engineer  

---

## 1. Executive Summary

This audit assesses the end-to-end telemetry, persistence, analytics, Copilot, and Streamlit dashboard implementations. While the mathematical reconciliation established in Phase 12.1 is sound, manual inspection and code tracing revealed several critical UX, semantic, and temporal consistency gaps that prevent the application from presenting as a cohesive, production-grade industrial control system.

---

## 2. Detailed Findings by Category

### A. UI State Issues
1. **Single-Response One-Shot Copilot:** The Copilot in `dashboard/app.py` stored only a single active response (`st.session_state["copilot_result"]`). Submitting a new query or clicking a quick-action replaced the entire view rather than maintaining an interactive conversational thread.
2. **Preset Mutation of Text Input:** Quick-action buttons overwrote the query text box via `st.session_state["copilot_query"] = clicked_query` instead of posting a new user chat message into an ongoing conversation.
3. **Widget State Cross-Contamination:** Changing machine dropdown options or clicking refresh could cause transient desynchronization between chat widgets and displayed analytics.

### B. Stale-Data Issues
1. **SLEEP State 1450 RPM Python Falsy Bug:**
   - *Code Location:* `api/demo.py` line 406: `"rpm": round(latest.rpm or 1450.0, 1)`.
   - *Mechanism:* In Python, `0.0 or 1450.0` evaluates to `1450.0` because `0.0` is falsy.
   - *Manifestation:* When a machine entered `SLEEP`, the simulator correctly output `rpm = 0.0`. However, the API converted `0.0` into `1450.0`, resulting in a machine displaying `SLEEP` and `1450 RPM` simultaneously.
   - *Fix:* Use explicit `latest.rpm if latest.rpm is not None else 0.0`.

### C. Time-Window Consistency Issues
1. **Unstated Analysis Window:** The dashboard failed to prominently display the authoritative contiguous analysis window (Start Timestamp, End Timestamp, Duration) on the overview screen. Users could not easily confirm whether a metric reflected the last 10 seconds or 60 seconds.
2. **Context Synchronization:** All 11 dashboard sections, the REST endpoints, and the Copilot must reference the identical 240-record window maintained in `demo_state`.

### D. Cumulative Meter vs Consumed Energy Issues
1. **Dial vs Interval Disconnect:**
   - In Section 4 (Fleet Table) and Section 5 (Deep Dive), the dashboard displayed both interval consumed energy ($0.0268\text{ kWh}$) and cumulative register ($100.0425\text{ kWh}$).
   - Without prominent explanatory labels, judges may question why the meter displays $100\text{ kWh}$ while total energy is $0.3962\text{ kWh}$.
   - *Fix:* Explicitly label `Energy Consumed (Analysis Window)` [CALCULATED] vs `Cumulative Meter Reading` [MEASURED], with clear contextual tooltips.

### E. Production Semantics Issues
1. **"3 Machines Producing" with 0 Units:**
   - *Code Location:* `api/demo.py` line 262: `"active_producing_machines": sum(1 for m in machine_status_list if m["state"] == "RUNNING")`.
   - *Mechanism:* Equated `state == "RUNNING"` with "producing units".
   - *Manifestation:* During early intervals or non-productive running periods where `production_count == 0`, the UI stated `Production: 0 units` alongside `3 machines producing`.
   - *Fix:* Distinguish `Machines Running (X/4)` from `Machines Actively Producing (Y/4)` and `Production Output (Z units)`.

### F. Forecast Consistency Issues
1. **Forecast Horizon & Interval Step Semantics:**
   - The forecast model outputs 5 discrete 1-minute interval predictions.
   - The UI line chart displays each step ($kWh/\text{minute}$), and the subtext displays the 5-minute aggregate sum.
   - *Verification:* The sum of the 5 points in `intervals` must equal `total_forecast_kwh` within $10^{-4}\text{ kWh}$.

### G. Copilot State & Conversational Issues
1. **Rigid Report Format for General Queries:**
   - `llm/fallback.py` formatted all responses with `Summary:`, `Evidence:`, `Interpretation:`, `Recommended Next Step:`.
   - Questions such as *"what u can do"* or *"what can you do"* received this mechanical formatting.
   - *Fix:* Tailor output style dynamically based on intent (conversational for `GENERAL_CHAT`, concise and structured for industrial analytics).
2. **Misleading Execution Mode Label:**
   - When answering general queries, the UI reported `Execution Mode: Grounded by Factory Analytics`.
   - *Fix:* Label as `GENERAL CONVERSATION` when in `GENERAL_CHAT` mode, and reserve `GROUNDED FACTORY ANALYTICS` for queries backed by authoritative metrics.

### H. Terminology & Provenance Label Issues
1. **Section 9 Savings Verification Semantics with Zero Production:**
   - When production is zero, SEC is undefined (`N/A`).
   - The UI showed `STATUS: NO_IMPROVEMENT`, implying an intervention had failed, when the real cause was insufficient production data.
   - *Fix:* Set status to `INSUFFICIENT DATA` when production is zero, explaining that production-normalized SEC verification requires non-zero output.
2. **Nominal Efficiency with Zero Production:**
   - If actual energy is below baseline during a zero-production window, labeling it "Nominal Efficiency" is misleading.
   - *Fix:* Clarify that energy is below baseline, but production efficiency cannot be confirmed without production output.

### I. Responsibility Boundary Integrity
1. **Person 1 Control Boundary:** Person 3 identifies energy and process optimization opportunities. All direct actuator, sleep mode trigger, or PLC control commands are owned by Person 1.
2. **Person 2 Health Boundary:** Vibration, temperature, anomaly score, and health score are ingested from Person 2 and presented purely as contextual operational signals without mechanical fault diagnosis.

---

## 3. Action Plan for Phase 13.1 Implementation

1. **Audit Document:** Deliver `docs/phase13_1_audit.md` (Complete).
2. **Fix `api/demo.py`:**
   - Resolve `latest.rpm or 1450.0` falsy bug.
   - Refactor `active_producing_machines` vs `running_machines`.
3. **Enhance `llm/context_builder.py` & `llm/fallback.py`:**
   - Support capability queries (*"what can you do"*, *"what u can do"*).
   - Dynamic, natural conversational output styles.
   - Handle zero-production SEC questions accurately.
4. **Overhaul `dashboard/app.py`:**
   - Implement `st.chat_message()` and `st.chat_input()` with session-state persistence.
   - Quick-action buttons submit genuine chat messages.
   - Clear chat and New Conversation controls.
   - Prominent Analysis Window display.
   - Accurate production and savings semantics (`INSUFFICIENT DATA`).
5. **Consistency Validator:** Build `scripts/validate_dashboard_consistency.py`.
6. **Copilot Demo Script:** Build `scripts/demo_copilot_conversation.py`.
7. **Regression Test Suite:** Add $\ge 30$ tests in `tests/test_phase13_1_hardening.py`.
