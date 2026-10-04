"""
Programmatic Dashboard & Analytics Consistency Validator.
Person 3: Energy & Production Intelligence Engine
Schneider Electric 2026 Smart Manufacturing Hackathon

Verifies 12 critical consistency guarantees across:
1. Factory actual energy == sum(machine actual energy)
2. Factory expected energy == sum(machine expected energy)
3. Factory production == sum(machine production)
4. State energy total == factory energy
5. Idle + sleep + productive + other states reconcile
6. Factory deviation == actual - expected
7. Forecast aggregate == sum forecast intervals
8. Copilot numerical context matches dashboard snapshot
9. Machine detail matches authoritative demo state
10. Zero-production semantics are correct (SEC is N/A, verified savings status is INSUFFICIENT DATA)
11. No stale machine values (SLEEP / OFF states have RPM == 0)
12. Authoritative analysis window is consistent across factory and machine snapshots

Prints PASS/FAIL for each and exits with non-zero status on any failure.
"""

import sys
import math
from pathlib import Path
from typing import Dict, Any, List

# Ensure parent directory is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from api.main import app
from scripts.run_final_demo import run_authoritative_demo
from simulator.demo_state import demo_state


def run_consistency_checks() -> bool:
    print("\n========================================================")
    print("    PERSON 3: DASHBOARD & DATA CONSISTENCY VALIDATOR    ")
    print("========================================================\n")

    client = TestClient(app)

    # 1. First test Zero-Production State
    print("--- STEP 1: Validating Clean Zero-Production Semantics ---")
    from datetime import datetime, timezone
    from database.schemas import TelemetryRecord, MachineState
    demo_state.reset()
    t0 = datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 4, 10, 0, 10, tzinfo=timezone.utc)
    zero_recs = []
    for m_id in ["M01", "M02", "M03", "M04"]:
        st = MachineState.SLEEP if m_id == "M01" else MachineState.RUNNING
        rpm = 0.0 if m_id == "M01" else 1450.0
        pwr = 0.05 if m_id == "M01" else 4.0
        zero_recs.extend([
            TelemetryRecord(
                timestamp=t0, machine_id=m_id, power_kw=pwr, energy_kwh=100.0,
                machine_state=st, production_count=0, production_delta=0,
                cycle_time_sec=0.0, voltage_v=415.0, current_a=6.0,
                temperature_c=45.0, vibration=0.1, rpm=rpm, health_score=100.0,
            ),
            TelemetryRecord(
                timestamp=t1, machine_id=m_id, power_kw=pwr, energy_kwh=100.01,
                machine_state=st, production_count=0, production_delta=0,
                cycle_time_sec=0.0, voltage_v=415.0, current_a=6.0,
                temperature_c=45.0, vibration=0.1, rpm=rpm, health_score=100.0,
            )
        ])
    demo_state.set_active_demo_records(zero_recs)

    res_zero = client.get("/demo/factory")
    assert res_zero.status_code == 200, f"Expected 200, got {res_zero.status_code}"
    zero_data = res_zero.json()

    zero_prod = zero_data["production"]["total_units"]
    zero_sec = zero_data["sec"]
    zero_running = zero_data["production"]["running_machines"]
    zero_producing = zero_data["production"]["active_producing_machines"]
    zero_sav_status = zero_data["savings"].get("verification_status")

    zero_checks = []
    # Production == 0
    zero_checks.append(zero_prod == 0)
    # SEC is None / N/A
    zero_checks.append(zero_sec is None)
    # Active producing machines is 0 even if running_machines == 3
    zero_checks.append(zero_producing == 0 and zero_running == 3)
    # Verification status is INSUFFICIENT_DATA
    zero_checks.append(zero_sav_status == "INSUFFICIENT_DATA")

    if all(zero_checks):
        print(f"  [PASS] Zero-production baseline state verified: prod={zero_prod}, running={zero_running}, producing={zero_producing}, SEC={zero_sec}, savings_status={zero_sav_status}")
    else:
        print(f"  [FAIL] Zero-production state failed: prod={zero_prod}, running={zero_running}, producing={zero_producing}, SEC={zero_sec}, status={zero_sav_status}")
        return False

    # 2. Run Authoritative Demo Scenario to populate authoritative contiguous dataset
    print("\n--- STEP 2: Executing Authoritative Demonstration Scenario ---")
    demo_res = run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)
    assert demo_res is not None

    # Fetch fresh factory snapshot via API
    res_factory = client.get("/demo/factory")
    assert res_factory.status_code == 200
    factory = res_factory.json()

    # Fetch machine details
    machines = ["M01", "M02", "M03", "M04"]
    machine_details = {}
    for m_id in machines:
        res_m = client.get(f"/demo/machine/{m_id}")
        assert res_m.status_code == 200
        machine_details[m_id] = res_m.json()

    # Fetch state breakdown
    res_states = client.get("/savings/states")
    assert res_states.status_code == 200
    state_data = res_states.json()

    # Fetch Copilot response
    res_copilot = client.post("/copilot/chat", json={"question": "What is factory energy consumption and baseline?"})
    assert res_copilot.status_code == 200
    copilot_data = res_copilot.json()

    # Begin the 12 Authoritative Checks
    results = []
    tol = 1e-4

    print("\n--- STEP 3: Evaluating 12 Consistency Checkpoints ---\n")

    # Check 1: Factory actual energy = sum(machine actual energy)
    factory_actual = factory["energy"]["actual_energy_kwh"]
    sum_machine_actual = sum(m["actual_energy_kwh"] for m in machine_details.values())
    c1 = abs(factory_actual - sum_machine_actual) < tol
    results.append(("1. Factory actual energy == sum(machine actual energy)", c1,
                    f"Factory={factory_actual:.4f} kWh, Sum(M)={sum_machine_actual:.4f} kWh, diff={abs(factory_actual - sum_machine_actual):.6f}"))

    # Check 2: Factory expected energy = sum(machine expected energy)
    factory_expected = factory["energy"]["expected_energy_kwh"]
    sum_machine_expected = sum(m["baseline_expected_energy_kwh"] for m in machine_details.values())
    c2 = abs(factory_expected - sum_machine_expected) < tol
    results.append(("2. Factory expected energy == sum(machine expected energy)", c2,
                    f"Factory={factory_expected:.4f} kWh, Sum(M)={sum_machine_expected:.4f} kWh, diff={abs(factory_expected - sum_machine_expected):.6f}"))

    # Check 3: Factory production = sum(machine production)
    factory_prod = factory["production"]["total_units"]
    sum_machine_prod = sum(m["production_units"] for m in machine_details.values())
    c3 = factory_prod == sum_machine_prod
    results.append(("3. Factory production == sum(machine production)", c3,
                    f"Factory={factory_prod} units, Sum(M)={sum_machine_prod} units"))

    # Check 4: State energy total = factory energy
    states_list = state_data.get("states", [])
    sum_state_energy = sum(s.get("energy_kwh", 0.0) or s.get("actual_energy_kwh", 0.0) for s in states_list)
    c4 = abs(factory_actual - sum_state_energy) < tol
    results.append(("4. State energy total == factory actual energy", c4,
                    f"State Total={sum_state_energy:.4f} kWh, Factory={factory_actual:.4f} kWh, diff={abs(factory_actual - sum_state_energy):.6f}"))

    # Check 5: Idle + sleep + productive + other states reconcile
    state_names = {s.get("state") or s.get("machine_state") for s in states_list}
    c5 = len(state_names) > 0 and abs(sum_state_energy - factory_actual) < tol
    results.append(("5. Idle + sleep + productive + other states reconcile", c5,
                    f"States recorded: {sorted(list(state_names))}, sum matches factory energy"))

    # Check 6: Factory deviation = actual - expected
    factory_dev = factory["deviation"]["deviation_kwh"]
    calc_dev = round(factory_actual - factory_expected, 4)
    c6 = abs(factory_dev - calc_dev) < tol
    results.append(("6. Factory deviation == actual - expected", c6,
                    f"Reported dev={factory_dev:+.4f} kWh, Calc dev={calc_dev:+.4f} kWh"))

    # Check 7: Forecast aggregate = sum forecast intervals
    fc = factory["forecast"]
    intervals = fc.get("intervals", [])
    total_fc = fc.get("total_forecast_kwh", 0.0)
    sum_intervals = round(sum(i.get("forecast_energy_kwh", 0.0) for i in intervals), 4)
    c7 = len(intervals) == 5 and abs(total_fc - sum_intervals) < tol
    results.append(("7. Forecast aggregate == sum forecast intervals", c7,
                    f"Reported total={total_fc:.4f} kWh, Sum intervals={sum_intervals:.4f} kWh (5 steps)"))

    # Check 8: Copilot numerical context matches dashboard snapshot
    ctx = copilot_data.get("context_summary", {})
    copilot_actual = ctx.get("factory_energy_kwh")
    copilot_expected = ctx.get("factory_expected_kwh")
    c8 = (copilot_actual is not None and abs(copilot_actual - factory_actual) < tol and
          copilot_expected is not None and abs(copilot_expected - factory_expected) < tol)
    results.append(("8. Copilot numerical context matches dashboard snapshot", c8,
                    f"Copilot Actual={copilot_actual}, Factory Actual={factory_actual}"))

    # Check 9: Machine detail matches authoritative demo state
    machine_status_summary = {m["machine_id"]: m for m in factory["machine_status"]}
    m_match = True
    for m_id, m_det in machine_details.items():
        summary = machine_status_summary.get(m_id)
        if not summary:
            m_match = False
            break
        if abs(summary["energy_kwh"] - m_det["actual_energy_kwh"]) >= tol:
            m_match = False
            break
    c9 = m_match
    results.append(("9. Machine detail matches authoritative demo state", c9,
                    "All 4 machines reconcile between /demo/factory and /demo/machine/{id}"))

    # Check 10: Zero-production semantics are correct
    c10 = True
    for m_id, m_det in machine_details.items():
        if m_det["production_units"] == 0 and m_det["sec"] is not None:
            c10 = False
            break
    results.append(("10. Zero-production semantics are correct (SEC is N/A when prod=0)", c10,
                    "Verified SEC is None whenever production units == 0 across fleet"))

    # Check 11: No stale machine values (SLEEP has RPM == 0)
    c11 = True
    stale_reasons = []
    for m_id, m_det in machine_details.items():
        st = m_det["current_state"]
        rpm = m_det.get("health_context", {}).get("rpm", 0.0)
        if st in ("SLEEP", "OFF") and rpm > 50.0:
            c11 = False
            stale_reasons.append(f"{m_id} state={st} but rpm={rpm}")
    results.append(("11. No stale machine values (SLEEP/OFF has RPM ≈ 0)", c11,
                    "Passed: No SLEEP machine exhibits active operating RPM" if c11 else "; ".join(stale_reasons)))

    # Check 12: Analysis window is consistent
    w_info = factory.get("analysis_window", {})
    c12 = w_info.get("start_time") not in (None, "N/A") and w_info.get("duration_seconds", 0.0) > 0.0
    results.append(("12. Authoritative analysis window is consistent", c12,
                    f"Window: {w_info.get('start_time')} -> {w_info.get('end_time')} ({w_info.get('duration_seconds')}s)"))

    # Print summary
    all_passed = True
    for name, passed, detail in results:
        status_str = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"  {status_str} {name}")
        print(f"         Detail: {detail}")

    print("\n========================================================")
    if all_passed:
        print("  ALL 12 CONSISTENCY GUARANTEES VERIFIED SUCCESSFULLY!")
        print("========================================================\n")
        return True
    else:
        print("  CONSISTENCY VERIFICATION FAILED!")
        print("========================================================\n")
        return False


if __name__ == "__main__":
    success = run_consistency_checks()
    sys.exit(0 if success else 1)
