# Phase 13 — Industrial Energy Intelligence Demonstrator Technical Report

## 1. Executive Summary & Objective

Phase 13 elevates the technically validated Person 3 Energy & Production Intelligence Engine into a presentation-grade, industrial energy-management control center for the **Schneider Electric 2026 Smart Manufacturing Hackathon**.

The design realizes the complete operational lifecycle:
$$\text{MEASURE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{COMPARE AGAINST BASELINE} \longrightarrow \text{DETECT DEVIATION} \longrightarrow \text{FORECAST} \longrightarrow \text{IDENTIFY OPPORTUNITIES} \longrightarrow \text{VERIFY SAVINGS} \longrightarrow \text{EXPLAIN TO OPERATOR}$$

### Key Milestones:
* **Presentation-Grade Interface:** Refactored `dashboard/app.py` into a streamlined industrial control room adhering to Schneider Electric visual and information architecture standards.
* **Zero Fabrication / Pure Provenance:** All metrics originate from authoritative Python analytics and FastAPI services. Zero formulas are duplicated in the presentation layer.
* **Clean Responsibility Boundaries:** Explicit segregation between Person 1 (power optimization/control), Person 2 (component mechanical health), Person 3 (energy/production intelligence), and Person 4 (cloud/central platform).
* **Deterministic Final Workflow:** Created `scripts/run_final_demo.py` with programmatic mathematical reconciliation assertions and structured output.
* **Test Suite Expansion:** Added `tests/test_phase13_dashboard.py` (16 tests). Total test suite stands at **250 passed, 0 failed**.

---

## 2. Reused Architecture & Pure Analytics Foundation

Phase 13 preserves and builds directly upon the frozen Phase 12.1 reconciliation architecture:

```
[Simulated Machines M01–M04] (Physics-based multi-phase simulation)
            ↓
     [Telemetry JSON] (factory/{id}/telemetry)
            ↓
      [MQTT Pipeline] (QoS 1 Pub/Sub with non-blocking subscriber)
            ↓
     [FastAPI Backend] (REST APIs + Lifespan management)
            ↓
    [Persistent Database] (SQLAlchemy / PostgreSQL / SQLite fallback)
            ↓
 [Authoritative Demo Window] (demo_state contiguous memory buffer)
            ↓
  [Deterministic Analytics] 
  ├── Energy (kWh, interval delta, peak kW)
  ├── Production (units, cycle times)
  ├── Specific Energy Consumption (SEC = kWh / unit)
  ├── Retrospective Baseline (production-aware ML)
  ├── Energy Deviation (actual vs expected, persistence tracking)
  ├── Short-Horizon Forecast (1–5 min GBDT multi-step)
  ├── Savings Intelligence (IPMVP-style normalized SEC verification)
  └── Optimization Opportunities (ranked priority recommendations)
            ↓
   [Grounded Copilot] (SLM narrative grounded strictly in Python facts)
            ↓
 [Streamlit Control Center] (Industrial Plotly interactive visual dashboard)
```

---

## 3. Dashboard Information Architecture & Sections

The dashboard (`dashboard/app.py`) is organized into 11 operational sections:

| # | Section | UI Component | Primary Purpose |
|---|---|---|---|
| **0** | **Demonstration Banner** | Top visual bar | Identifies simulation context and defines `[MEASURED]`, `[CALCULATED]`, `[PREDICTED]`, `[RECOMMENDED]` badges. |
| **1** | **Factory Overview KPIs** | 8 compact metric cards | High-level operational pulse: Total Energy, Production, SEC, Baseline, Deviation, Cost, CO₂, Potential Savings. |
| **2** | **Energy vs Production** | Plotly Scatter Plot | Relates machine energy draw against production output. Identifies high-energy non-productive assets. |
| **3** | **Actual vs Baseline** | Plotly Grouped Bar | Compares aggregate actual energy against model-based expected baseline with status classification. |
| **4** | **Machine Fleet Table** | Streamlit Dataframe | Tabular overview of all 4 assets (`M01`–`M04`) with state, power, consumed energy, meter dials, SEC, and health context. |
| **5** | **Asset Deep-Dive** | Interactive Columns | In-depth operational, energy, baseline, and Person 2 health context metrics for any selected machine. |
| **6** | **Operating State Energy** | Plotly Bar Chart | Bar chart breakdown of energy by state (`RUNNING`, `IDLE`, `SLEEP`, `DEGRADED`, `OVERLOAD`). No pie charts. |
| **7** | **Non-Production Energy** | Highlight Cards | Details energy consumed during `IDLE` (unproductive draw) vs `SLEEP` (curtailed standby). |
| **8** | **Short-Horizon Forecast** | Plotly Line Chart | 1–5 minute recursive forward demand projection with model metadata (`GradientBoostingRegressor`). |
| **9** | **Savings & Verification** | Dual-Panel Card | Strict separation of **Potential Gross Savings** ($\max(0, \text{Dev})$) vs **Verified Savings** (IPMVP Option B). |
| **10** | **Optimization Engine** | Ranked Opportunity Cards | Top efficiency recommendations categorized by deviation, idle reduction, maintenance alignment, or throughput. |
| **11** | **Energy Copilot** | Interactive Query Box | Natural-language query interface with quick-action prompts, grounded response, and evidence context accordion. |

---

## 4. Key Performance Indicator (KPI) Definitions

| KPI | Unit | Provenance | Mathematical Definition |
|---|---|---|---|
| **Total Energy** | $\text{kWh}$ | `[CALCULATED]` | $\sum_{m} (E_{\text{end}, m} - E_{\text{start}, m})$ over contiguous session intervals |
| **Production Count** | $\text{units}$ | `[MEASURED]` | $\sum_{m} \Delta \text{Units}_m$ produced during analysis window |
| **Factory SEC** | $\text{kWh/unit}$ | `[CALCULATED]` | $\frac{\text{Total Energy Consumed}}{\text{Total Production Units Produced}}$ |
| **Expected Baseline** | $\text{kWh}$ | `[PREDICTED]` | $\sum_{m} \hat{E}_m(f(\text{production}, \text{state}, \Delta t, \text{health}))$ |
| **Energy Deviation** | $\text{kWh}$ | `[CALCULATED]` | $\text{Actual Energy} - \text{Expected Energy}$ |
| **Deviation %** | $\%$ | `[CALCULATED]` | $\frac{\text{Deviation kWh}}{\text{Expected Energy kWh}} \times 100\%$ |
| **Potential Savings** | $\text{kWh}$ | `[CALCULATED]` | $\max(0, \text{Deviation kWh})$ |
| **Energy Cost** | $₹$ | `[CALCULATED]` | $\text{Total Energy} \times \text{Tariff (₹8.50/kWh)}$ |
| **Carbon Footprint** | $\text{kg CO}_2$ | `[CALCULATED]` | $\text{Total Energy} \times \text{Grid Emission Factor (0.716 kg/kWh)}$ |

---

## 5. Strict Data Provenance Framework

To guarantee industrial trust, every metric displayed in the dashboard is tagged with its origin:

* **`[MEASURED]`**: Direct sensor readings from simulator physical equations (e.g. Active Power in kW, Voltage in V, Current in A, Cumulative Meter Dial in kWh, Production Delta).
* **`[CALCULATED]`**: Deterministic mathematical calculations from interval deltas (e.g. Consumed Energy in window, Specific Energy Consumption, Energy Cost, Avoided Emissions).
* **`[PREDICTED]`**: Machine learning model inferences without electrical data leakage (e.g. Production-aware baseline energy, 1–5 minute forward energy demand).
* **`[RECOMMENDED]`**: Analytical optimization opportunities and suggested operator actions generated by the heuristic ranking engine.
* **`[PERSON 2]`**: Contextual machine health signals ingested from Person 2's layer (Health Score, Anomaly Score, Temperature, Vibration).

---

## 6. Responsibility Boundary Guardrails

The demonstrator adheres strictly to hackathon person boundaries:

1. **Person 1 (Control & Optimization):**
   * Person 3 calculates the energy and financial benefit of transitions (e.g. IDLE → ECO SLEEP).
   * Person 3 **never** issues direct PLC, actuator, or motor shut-off commands.
   * Suggested actions are phrased: *"Evaluate with machine control / power optimization layer."*

2. **Person 2 (Predictive Maintenance & Health):**
   * Person 3 accepts temperature, vibration RMS, motor RPM, and health scores as contextual operational conditions.
   * Person 3 **never** claims component mechanical failure diagnoses (e.g. *"bearing failure"*).
   * Phrased: *"Contextual health signals ingested from Person 2. Component fault diagnosis belongs to Person 2."*

3. **Person 3 (Energy & Production Intelligence):**
   * Full ownership of Specific Energy Consumption (SEC), baseline modeling, deviation tracking, short-horizon forecasting, savings quantification, and natural-language explanations.

---

## 7. Energy Copilot Aligned Demonstration Questions

To avoid logically contradictory demonstrations, the default question was updated from the previous leading question (*"Why is factory energy consumption above baseline?"*) to an aligned, neutral question:

> **Default Question:** *"What is the factory energy consumption and how does it compare with baseline?"*

### Additional Quick-Action Prompts:
* 🏭 **Factory Baseline:** *"What is the factory energy consumption and how does it compare with baseline?"*
* ⚠️ **Top Opportunity:** *"Which machine requires the most attention and why?"*
* 💤 **Idle Energy Analysis:** *"Why is machine M01 consuming energy when production is zero?"*
* 🔍 **Machine M01 Status:** *"What is the status of machine M01?"*
* 🔮 **5-Min Forecast:** *"What is the short-horizon forecast for the next 5 minutes?"*

When Ollama is unavailable, the deterministic fallback generates evidence-grounded prose using the exact authoritative window numbers, guaranteeing zero crashes and zero hallucinations.

---

## 8. Authoritative Final Demo Output (`scripts/run_final_demo.py`)

Executing `python scripts/run_final_demo.py` yields the 15-step sequence with programmatic reconciliation verification:

```
========================================================
   PERSON 3: SMART MANUFACTURING ENERGY & PRODUCTION    
                INTELLIGENCE ENGINE                     
     Schneider Electric 2026 Hackathon Demonstration    
========================================================

[1/15] Initializing persistent database and resetting demo state buffer...
       -> Database: CONNECTED
       -> Demo state: RESET to clean nominal baseline
       -> MQTT Broker offline. Using validated in-process serialization & subscriber.
[2/15] Initializing physical factory simulator (4 machines, seed=42)...
[3/15] Executing 6-phase operational scenario and streaming telemetry:
       * PHASE_A_NORMAL: Nominal factory production across M01..M04
       * PHASE_B_IDLE: M01 transitions to IDLE (unproductive energy draw)
       * PHASE_C_SLEEP: M01 commanded to ECO SLEEP (energy curtailment)
       * PHASE_D_DEGRADED: M03 undergoes mechanical degradation (excess energy)
       * PHASE_E_OVERLOAD: M02 experiences electrical & mechanical overload
       * PHASE_F_RECOVERY: M03 repaired and M02 restored to RUNNING

[4/15] Authoritative demo window established: 240 records persisted.
[5/15] Computing deterministic interval energy consumption...
[6/15] Computing production unit counts...
[7/15] Computing Specific Energy Consumption (SEC = Total Energy / Total Units)...
[8/15] Evaluating production-aware machine baselines...
[9/15] Computing energy deviations...
[10/15] Calculating potential savings and emissions impact...
[11/15] Evaluating prioritized optimization opportunities...
[12/15] Generating short-horizon multi-step energy forecast...
[13/15] Querying grounded Energy Copilot with aligned question...
[14/15] Validating mathematical reconciliation across factory and machine metrics...
       -> Programmatic Reconciliation: 100% PASSED

==================================================
FINAL FACTORY INTELLIGENCE SUMMARY
==================================================
Machines: 4
Telemetry: 240
Production: 3 units
Actual Energy: 0.3962 kWh
Expected Energy: 0.7923 kWh
Deviation: -0.3961 kWh (-50.00%)
SEC: 0.1321 kWh/unit
Potential Savings: 0.0000 kWh (₹0.00)
Energy Cost: ₹3.37
CO₂: 0.2836 kg
Forecast: Next 5 minutes: 0.0396 kWh
Top Opportunity: M01 (IDLE_REDUCTION) - IDLE state accounts for 28.36% of total electrical consumption (0.0076 kWh).
Demo Status: COMPLETED (Authoritative Window)
==================================================

Copilot Query: "What is the factory energy consumption and how does it compare with baseline?"
Copilot Answer:
Summary:
Factory electrical energy consumption is currently 0.39615 kWh versus an expected baseline of 0.792255 kWh (0.0 kWh potential savings opportunity).

Evidence:
Actual Energy: 0.39615 kWh | Expected Baseline: 0.792255 kWh | Production: 3 units | Actual SEC: 0.1321 kWh/unit | Expected Baseline SEC: 0.2641 kWh/unit | Potential Cost Savings: ₹0.0.

Interpretation:
Energy consumption is operating within or below expected baseline tolerances.

Recommended Next Step:
Maintain current operational schedule and monitor real-time telemetry.
==================================================
```

---

## 9. Comprehensive Test Suite Verification

A dedicated test suite `tests/test_phase13_dashboard.py` was introduced containing 16 unit and integration checks:
1. `test_1_dashboard_imports_and_formatting_helpers`: Safe handling of `NaN`, `inf`, and `None`.
2. `test_2_dashboard_can_retrieve_factory_data`: Full `/demo/factory` response schema validation.
3. `test_3_dashboard_can_retrieve_machine_data`: Fleet-wide `/demo/machine/{id}` detail validation.
4. `test_4_factory_energy_reconciliation`: $\text{Factory Energy} = \sum \text{Machine Energy}$ ($\Delta < 10^{-4}\text{ kWh}$).
5. `test_5_expected_energy_reconciliation`: $\text{Factory Expected} = \sum \text{Machine Expected}$ ($\Delta < 10^{-4}\text{ kWh}$).
6. `test_6_production_reconciliation`: $\text{Factory Production} = \sum \text{Machine Production}$ ($3 = 3$).
7. `test_7_deviation_arithmetic_validity`: $\text{Deviation} = \text{Actual} - \text{Expected}$ across all assets.
8. `test_8_no_cumulative_meter_double_counting`: Consumed energy verified as interval ($< 2.0\text{ kWh}$), not cumulative dial.
9. `test_9_forecast_data_labeled_predicted`: 5-step projections verified with model metadata.
10. `test_10_savings_status_distinguished_from_potential_savings`: Potential savings ($\max(0, \text{Dev})$) vs IPMVP verified savings.
11. `test_11_missing_ollama_does_not_crash_copilot`: Verified deterministic fallback accuracy when Ollama is offline.
12. `test_12_missing_api_does_not_crash_dashboard`: Graceful error handling for missing endpoints.
13. `test_13_missing_production_produces_safe_sec_behavior`: Safe formatting when production count is 0.
14. `test_14_machine_selection_coverage`: Profile configuration integrity for `M01` through `M04`.
15. `test_15_demo_reset_is_deterministic`: Demo buffer reset and reproducible executions.
16. `test_16_authoritative_demo_reconciliation`: End-to-end 15-step sequence reconciliation.

### Complete Pytest Execution:
```bash
pytest -q
```
**Result: 250 passed, 0 failed in 46.45s** (234 existing + 16 new Phase 13 tests).

---

## 10. How to Launch the Demonstration

### Terminal 1: (Optional) Run the Authoritative Final Demo Script
```bash
python scripts/run_final_demo.py
```

### Terminal 2: Start the FastAPI Engine
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 3: Launch the Industrial Dashboard
```bash
streamlit run dashboard/app.py
```

---

## 11. Known Limitations & Future Roadmap

1. **Browser GUI Testing Boundary:**
   The test suite performs comprehensive import, mock API, and client tests. Live browser DOM interaction was not executed within headless CI environments.
2. **Local Small Language Model:**
   The Copilot defaults to `qwen3:1.7b` via Ollama. If the model is not pulled, the system seamlessly uses the deterministic Python analytics fallback.
3. **Multi-Tenant Factory Scaling:**
   Current architecture supports a 4-asset industrial cell (`M01`–`M04`). Future enhancements could scale to multi-cell hierarchies with edge gateway clustering.
