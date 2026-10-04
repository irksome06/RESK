# Phase 12.1 Data Reconciliation & Consistency Audit

## 1. Executive Summary & Problem Statement

In the Phase 12 integration demo, an inconsistency was identified between the factory summary metrics and the Copilot explanation:
- **Factory Demo Summary:**
  - Energy: `0.40 kWh` (Expected: `0.79 kWh`)
  - Production: `3 units`
  - SEC: `0.1321 kWh/unit`
  - Top Opportunity identified: `M01` (due to IDLE state accounting for 28.36% of electrical consumption, 0.0076 kWh).
- **Copilot Narrative Output:**
  - "Machine M01 is in RUNNING state, consuming 25.57377 kWh compared to an expected baseline of 0.005634 kWh (+25.5681 kWh, +453818.53% deviation, status: ABOVE_BASELINE)."

This audit traces the root cause of this discrepancy across all subsystems and defines the mathematical and architectural standardization required for 100% data reconciliation.

---

## 2. Root Cause Analysis

### 2.1 The 25.57 kWh Phantom Jump: Cross-Session Database Leakage
1. **Database Persistence History:**
   The SQLite database (`energy_intelligence.db`) retains telemetry inserted by earlier unit tests (e.g. `test_telemetry.py` with hardcoded `energy_kwh = 125.6 kWh` and `test_persistence_integrity` with `energy_kwh = 102.34 kWh`).
2. **Disjoint Meter Registers:**
   When `sim = FactorySimulator(seed=42)` initialized for the demo run, its internal meter began at its configured nominal baseline (`100.002 kWh`), accumulating up to `100.0058 kWh` over the 60-second scenario.
3. **Unbounded Recency Slicing in Context Builder:**
   In `llm/context_builder.py`, `_load_telemetry(machine_id="M01", limit=30)` called `telemetry_store.get_recent(limit=30, machine_id="M01")`, which executed:
   ```sql
   SELECT * FROM telemetry WHERE machine_id='M01' ORDER BY timestamp DESC LIMIT 30;
   ```
   This 30-record slice captured:
   - 12 newly simulated records with `energy_kwh` from `100.002` to `100.0058` kWh.
   - 2 historical test records from prior days with `energy_kwh = 102.34` and `energy_kwh = 125.6` kWh.
4. **Interval Delta Calculation:**
   When sorted chronologically, the algorithm evaluated:
   $$\Delta E = e_{curr} - e_{prev} = 125.60000 - 100.02623 = 25.57377\text{ kWh}$$
   This 25.57 kWh difference was an artifact of joining two completely disjoint simulation runs with different initial meter values.

### 2.2 Intent Routing Misattribution
- Question asked: `"Why is factory energy consumption above baseline?"`
- The deterministic classifier matched `"above baseline"` to intent `ENERGY_DEVIATION`.
- Because the question referred to the *factory* (no specific machine specified, `target_machine = None`), line 220 in `llm/context_builder.py` arbitrarily defaulted:
  ```python
  m_id = target_machine or "M01"
  ```
  Instead of evaluating factory-wide deviation and reporting the top contributor, it forced single-machine analysis on M01 using the corrupted slice.

### 2.3 Window Decoupling
- `run_factory_demo.py` computed factory KPIs strictly over `received_records` (the 240 records generated during the 60-second demo run).
- `context_builder.py` independently queried the database for 30 records without filtering by the demo's time window (`demo_start_time` to `demo_end_time`).
- Result: The factory snapshot and the Copilot operated on completely different time horizons and data windows.

---

## 3. End-to-End Data Flow Mapping

| Stage | Input Source | Window / Filtering | Calculation Method | Observed Inconsistency |
|---|---|---|---|---|
| **1. Simulation** | `FactorySimulator.step()` | 60 seconds (6 phases × 10 steps) | Physics models (`P_active`, `Q_reactive`, thermal, `energy_kwh`) | None. Monotonic within run. |
| **2. Ingestion** | MQTT Subscriber callback | Single-event ingestion | Appends to DB & `telemetry_store` | None. Deduplication active. |
| **3. Demo Analytics** | `received_records` in runner | Exact demo run ($t_0$ to $t_{60}$) | `compute_factory_efficiency(records)` | Factory energy = 0.40 kWh (Correct). |
| **4. Demo API (`/demo/factory`)** | `_load_demo_telemetry()` | `limit=60` newest records | `compute_machine_savings()` per machine | Susceptible to cross-run boundary if DB has older records. |
| **5. Copilot Context** | `_load_telemetry()` | `limit=30` newest records | Independent query without demo window | Picked up 25.57 kWh cross-session jump. |
| **6. Copilot Output** | `llm/fallback.py` | Context JSON from Step 5 | Deterministic template using context values | Cited 25.57 kWh because context contained it. |

---

## 4. Standardization & Remediation Plan

1. **Standardize Analysis Window:**
   - Establish `demo_state.get_demo_window()` storing `window_start` and `window_end` (UTC) and the active demo records.
   - When running the demo or querying `/demo/factory`, `/demo/machine/{id}`, or `/copilot/chat`, all components must filter telemetry strictly within the active demo window $[t_{start}, t_{end}]$.
2. **Prevent Cross-Session Meter Reset Leaks:**
   - In `compute_machine_deviation_from_records` (`analytics/deviation.py`), reject intervals where:
     - $dt \le 0$ or $dt > 30.0$ seconds (detects time gaps between independent test/demo sessions).
     - $\Delta E > (P_{rated\_max} \times \frac{dt}{3600}) \times 2.5$ (detects impossible physical power spikes caused by meter register mismatches).
3. **Pass Authoritative Window to Context Builder:**
   - Extend `context_builder.build_context()` to accept optional `window_start`, `window_end`, or explicit `records`.
   - When a factory question is asked (`target_machine is None`), compute factory-level deviation and highlight the top contributing machine rather than arbitrarily defaulting to M01.
4. **Reconcile Factory and Machine Metrics:**
   - $\sum_{i=1}^4 \text{Machine Energy}_i = \text{Factory Energy} \pm 10^{-4}\text{ kWh}$.
   - $\sum_{i=1}^4 \text{Machine Production}_i = \text{Factory Production}$.
   - $\sum_{\text{state}} \text{State Energy} = \text{Factory Energy} \pm 10^{-4}\text{ kWh}$.
   - Potential Savings = $\max(0, \text{Actual} - \text{Expected})$ for the exact same window.
5. **Add Comprehensive Reconciliation Tests:**
   - Add tests to `tests/test_phase12_integration.py` ensuring mathematical identity across all subsystems.
