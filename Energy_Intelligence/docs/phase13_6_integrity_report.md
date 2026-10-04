# PHASE 13.6 — COPILOT & DASHBOARD INTEGRITY VERIFICATION REPORT

**Project:** Person 3 — Energy & Production Intelligence Engine  
**Challenge:** Smart Manufacturing — Industrial Energy & Process Efficiency  
**Hackathon:** Schneider Electric 2026 Hackathon  
**Phase:** 13.6 — Copilot & Dashboard Integrity Fix  
**Date:** October 2026  
**Status:** COMPLETE & VERIFIED  

---

## 1. Primary Objectives

Phase 13.6 implemented a surgical, non-destructive integrity pass addressing subtle semantic, Copilot routing, machine identity, and provenance issues identified during manual dashboard review:
1. **Dynamic Copilot Grounding:** Ensure quick-action buttons supply predefined *questions*, not predefined *answers*. All Copilot answers must be dynamically calculated and grounded in current authoritative telemetry.
2. **Domain Intent Separation:** Implement a clean separation between industrial factory intents (`FACTORY_DOMAIN`) and conversational / personal queries (`GENERAL_CHAT`). Prevent general queries from leaking factory numbers.
3. **Personal Question Safety:** Ensure questions like *"What is my name?"* or *"Who are you?"* never invent user identity or claim personal knowledge.
4. **Machine ID & Name Single Source of Truth:** Eliminate conflicting machine labels between the fleet table and the deep-dive / sidebar selectors by deriving all display names from canonical engineering specifications (`DEFAULT_PROFILES`).
5. **Authoritative Demo Window for State Energy:** Ensure IDLE, SLEEP, and RUNNING energy breakdowns are computed deterministically over the complete 240-record scenario.
6. **Provenance Label Integrity:** Correctly badge deterministically derived values as `[CALCULATED]` (e.g., Baseline Deviation) and model outputs as `[PREDICTED]` (e.g., Expected Baseline).
7. **Grounding Accuracy Claim:** Replace the unscientific claim of *"Zero Hallucination"* with the technically rigorous *"Grounding Validation: PASSED"*.
8. **Reconciliation Guarantees:** Preserve 100% mathematical reconciliation ($\Delta < 10^{-4}\text{ kWh}$) across all modules.

---

## 2. Comprehensive Audit Findings

Prior to making any edits, an extensive audit was performed across `dashboard/app.py`, `api/`, `llm/`, `simulator/`, `analytics/`, and `tests/`:

| Component | Status Before 13.6 | Audit Finding & Integrity Assessment |
|---|---|---|
| **Phase 12.1 / 13 Reconciliation** | Correct | Factory actual energy ($0.3962\text{ kWh}$) exactly equaled the sum of machine energies; production and SEC reconciled within $10^{-4}$. |
| **Copilot Dynamic Grounding** | Correct | No hardcoded numeric answers found in `llm/`. Output was synthesized dynamically from structured context. |
| **Copilot Intent Classification** | Broken | `classify_intent` routed unclassified questions to `GENERAL`. In `build_context` and `fallback.py`, `GENERAL` was bundled with `FACTORY_SUMMARY`, leaking factory kWh metrics for personal questions (*"What is my name?"* returned factory energy!). |
| **Machine Name Uniformity** | Broken | `dashboard/app.py` hardcoded mismatched machine names in sidebar (`M01 - Stamping Press`, `M03 - Plastic Injection Molding`), while the fleet table used canonical profiles (`M01 - CNC Milling Center 1`, `M03 - Stamping Press 3`). |
| **Section 5 Provenance Badge** | Broken | Baseline Deviation in deep dive card 3 was tagged `[PRED]` instead of `[CALC]`. |
| **UI Grounding Claim** | Defective | Displayed `Passed (Zero Hallucination)`, an unsubstantiated scientific claim. |
| **Snapshot Caching in `api/demo.py`** | Defective | `return DemoFactorySnapshotResponse(...)` executed prior to `demo_state.set_active_demo_snapshot`, leaving the caching call unreachable. |
| **Responsibility Boundaries** | Correct | Person 1 (no control commands) and Person 2 (no mechanical failure predictions) safeguards were active in validator. |

---

## 3. Root Cause Analysis

1. **Conflated Intent Fallback:** `llm/context_builder.py` mapped unrecognized queries to `GENERAL`, which was grouped with `FACTORY_SUMMARY` (`if intent in ["FACTORY_SUMMARY", "GENERAL"]:`). This populated `factory_summary` structured data for any question, causing `llm/fallback.py` to output factory kWh figures for questions like *"What is my name?"* or *"What is machine learning?"*.
2. **Duplicate Machine Registries:** Machine labels in `dashboard/app.py` were manually hardcoded as UI mock strings rather than referencing the canonical `DEFAULT_PROFILES` dictionary imported from `simulator/machine_simulator.py`.
3. **Badge Copy-Paste Typo:** The metric card for Baseline Deviation was adapted from the Expected Baseline card, retaining the `[PRED]` class rather than `[CALC]`.

---

## 4. Files Modified & Roles

- `llm/context_builder.py`:
  - Implemented explicit `GENERAL_CHAT` intent with regex patterns for personal/general questions.
  - Isolated `build_context()` for `GENERAL_CHAT`: returns zero factory metrics, empty grounded facts, and a clean domain notice.
  - Decoupled `FACTORY_SUMMARY` so it only triggers on explicit factory/plant inquiries.
- `llm/fallback.py`:
  - Separated `FACTORY_SUMMARY` from `GENERAL_CHAT`.
  - Added dedicated deterministic fallback handlers for `GENERAL_CHAT` (personal identity protection, ML definition, Python definition, assistant scope) without any factory numbers.
- `llm/prompts.py`:
  - Added Rule 9 to `COPILOT_SYSTEM_PROMPT` prohibiting personal data fabrication.
  - Updated `build_copilot_prompt` to provide tailored general-chat instructions.
- `api/demo.py`:
  - Fixed dead code in `get_demo_factory`: cached snapshot in `demo_state` before returning.
- `dashboard/app.py`:
  - Added `get_machine_display_name(machine_id)` helper deriving display names strictly from `DEFAULT_PROFILES`.
  - Updated sidebar fleet navigation and Section 5 asset radio selector to use `get_machine_display_name`.
  - Corrected Baseline Deviation badge to `<span class="badge badge-calc">[CALC]</span>`.
  - Replaced `Passed (Zero Hallucination)` with `PASSED`.
- `tests/test_phase13_6_integrity.py`:
  - Added 26 comprehensive regression and integrity tests.

---

## 5. Copilot Architecture & Domain Separation

The Copilot architecture now provides clear separation between factory-specific analytical reasoning and general/conversational inquiries:

```
                      USER QUESTION
                            |
           +----------------+----------------+
           |                                 |
    Factory/Asset Query?             General/Personal?
           |                                 |
           v                                 v
   Industrial Intent                   GENERAL_CHAT
  (FACTORY_SUMMARY,                          |
   MACHINE_ANALYSIS,                         v
   ENERGY_DEVIATION, etc.)           Isolated Context
           |                       (Zero Factory Numbers,
           v                        Zero Identity Claims)
 Authoritative Analytics                     |
 (Python SEC, Deviation, etc.)               v
           |                        Concise Explanation /
           v                         Deterministic Fallback
 Grounded Explanation
 (Strict Numerical Checks)
```

### Response Comparison:

| User Query | Detected Intent | Grounded Response Behavior |
|---|---|---|
| *"What is my name?"* | `GENERAL_CHAT` | Declines personal profile access: *"I do not possess personal profile information or user identity data in the factory Copilot context."* Zero factory numbers. |
| *"What is machine learning?"* | `GENERAL_CHAT` | Explains ML concept concisely: *"Machine learning (ML) is a computational discipline where statistical models learn empirical patterns..."* Zero factory numbers. |
| *"Explain Python."* | `GENERAL_CHAT` | Explains Python's role: *"Python is an interpreted, high-level programming language widely used in data engineering..."* Zero factory numbers. |
| *"What is the factory energy consumption?"* | `FACTORY_SUMMARY` | Pulls authoritative snapshot: actual energy ($0.3962\text{ kWh}$), baseline ($0.7923\text{ kWh}$), SEC ($0.1321\text{ kWh/unit}$). |
| *"What is the operational status of M01?"* | `MACHINE_ANALYSIS` | Analyzes M01 specifically: actual energy ($0.0268\text{ kWh}$), operating state (`RUNNING`/`IDLE`), SEC. |
| *"What are the top opportunities?"* | `OPPORTUNITIES` | Identifies M01 `IDLE_REDUCTION` with priority score ($85/100$) and estimated savings. |
| *"What is the 5-min forecast?"* | `FORECAST` | Multi-step projection from `GradientBoostingRegressor` ($0.0396\text{ kWh}$). |

---

## 6. Machine Identity Single Source of Truth

All machine representations throughout the system now derive exclusively from `DEFAULT_PROFILES`:

| Machine ID | Canonical Profile Name (`DEFAULT_PROFILES`) | Display Format (`get_machine_display_name`) | Fleet Table | Sidebar Navigation | Deep-Dive Selector |
|---|---|---|---|---|---|
| **M01** | CNC Milling Center 1 | `M01 - CNC Milling Center 1` | Verified | Verified | Verified |
| **M02** | Heavy Lathe 2 | `M02 - Heavy Lathe 2` | Verified | Verified | Verified |
| **M03** | Stamping Press 3 | `M03 - Stamping Press 3` | Verified | Verified | Verified |
| **M04** | Precision Grinder 4 | `M04 - Precision Grinder 4` | Verified | Verified | Verified |

---

## 7. State-Energy & Opportunity Window Reconciliation

Over the authoritative 240-record demonstration window:
- **RUNNING:** $0.29744\text{ kWh}$ ($156$ samples)
- **IDLE:** $0.00380\text{ kWh}$ ($10$ samples, M01 Phase B)
- **SLEEP:** $0.00389\text{ kWh}$ ($40$ samples, M01 Phase C)
- **DEGRADED:** $0.05669\text{ kWh}$ ($20$ samples, M03 Phase D)
- **OVERLOAD:** $0.03433\text{ kWh}$ ($10$ samples, M02 Phase E)
- **Total State Energy:** $0.39615\text{ kWh}$
- **Total Factory Energy:** $0.39615\text{ kWh}$
- **Reconciliation Delta:** $0.00000\text{ kWh}$ ($100\%$ exact within floating-point tolerance $< 10^{-4}\text{ kWh}$).

The opportunity engine evaluates this complete contiguous window, successfully detecting the M01 `IDLE_REDUCTION` opportunity ($28.36\%$ of M01 energy during idle).

---

## 8. Provenance & Scientific Integrity

- **Direct Ingestion Telemetry:** `[MEASURED]` (Power kW, Meter Dial kWh, State, Production Count, Temperature, Vibration).
- **Deterministic Python Analytics:** `[CALCULATED]` (Consumed Interval Energy, Factory SEC, Energy Cost, Avoided $\text{CO}_2$, Baseline Deviation).
- **Machine Learning Inference:** `[PREDICTED]` (Expected Production-Aware Baseline, 5-Minute Gradient Boosting Forecast).
- **Process Optimization Guidance:** `[RECOMMENDED]` (Prioritized Opportunities).
- **Hallucination Claim:** Replaced `Passed (Zero Hallucination)` with `Grounding Validation: PASSED`.

---

## 9. Test Suite Verification

### Execution Summary:
- **Previous Passing Tests:** 269
- **New Tests Added (Phase 13.6):** 26
- **Total Tests:** 295
- **Passed:** 295
- **Failed:** 0
- **Warnings:** 50 (standard third-party deprecation / numpy div-by-zero notices)
- **Total Execution Time:** ~62 seconds
- **Pass Rate:** 100.0%

---

## 10. Conclusion

Phase 13.6 completely resolved all semantic inconsistencies, machine name contradictions, provenance badge mislabelings, and Copilot context leakage without introducing new ML models, changing established simulator physics, or modifying frozen Phase 12.1/13 analytical code. The system is structurally robust, dynamically grounded, and hackathon ready.
