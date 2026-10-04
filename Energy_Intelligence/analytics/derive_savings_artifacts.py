"""
Script to derive Phase 10 artifacts:
1. data/processed/savings_analysis_data.csv
2. data/processed/savings_experiment_results.json
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from database.schemas import TelemetryRecord, MachineState
from analytics.savings import compute_machine_savings, verify_savings, calculate_roi_payback
from analytics.efficiency import compute_factory_efficiency, compute_state_efficiency
from analytics.optimization import opportunity_engine
from simulator.machine_simulator import DEFAULT_PROFILES
from simulator.config import settings

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_CSV = os.path.join(BASE_DIR, "data", "raw", "factory_telemetry.csv")
SAVINGS_CSV = os.path.join(BASE_DIR, "data", "processed", "savings_analysis_data.csv")
SAVINGS_JSON = os.path.join(BASE_DIR, "data", "processed", "savings_experiment_results.json")


def generate_savings_artifacts():
    print(f"Reading raw telemetry from {RAW_CSV}...")
    df = pd.read_csv(RAW_CSV)

    records_by_machine = {}
    all_records = []

    for _, row in df.iterrows():
        try:
            ts = pd.to_datetime(row["timestamp"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            rec = TelemetryRecord(
                timestamp=ts,
                machine_id=str(row["machine_id"]),
                power_kw=float(row["power_kw"]),
                energy_kwh=float(row["energy_kwh"]),
                machine_state=MachineState(str(row["machine_state"])),
                production_count=int(row.get("production_count", 0)),
                production_delta=int(row.get("production_delta", 0)),
                cycle_time_sec=float(row.get("cycle_time_sec", 0.0)),
                voltage_v=float(row["voltage_v"]) if pd.notna(row.get("voltage_v")) else 415.0,
                current_a=float(row["current_a"]) if pd.notna(row.get("current_a")) else 10.0,
                temperature_c=float(row["temperature_c"]) if pd.notna(row.get("temperature_c")) else 50.0,
                vibration=float(row["vibration"]) if pd.notna(row.get("vibration")) else 0.18,
                rpm=float(row["rpm"]) if pd.notna(row.get("rpm")) else 1450.0,
                torque_nm=float(row["torque_nm"]) if pd.notna(row.get("torque_nm")) else 0.0,
                health_score=float(row["health_score"]) if pd.notna(row.get("health_score")) else 100.0,
                anomaly_score=float(row["anomaly_score"]) if pd.notna(row.get("anomaly_score")) else 0.0,
                source="simulator",
            )
            records_by_machine.setdefault(rec.machine_id, []).append(rec)
            all_records.append(rec)
        except Exception:
            continue

    # 1. Compute Savings per Machine
    tariff = settings.ELECTRICITY_COST_INR_PER_KWH
    factor = settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH

    machine_summaries = []
    for m_id in sorted(records_by_machine.keys()):
        recs = records_by_machine[m_id]
        m_sav = compute_machine_savings(recs, tariff_inr=tariff, emission_factor_kg=factor)
        machine_summaries.append(m_sav)

    # 2. Compute Factory Efficiency
    factory_eff = compute_factory_efficiency(records_by_machine, tariff_inr=tariff, emission_factor_kg=factor)

    # 3. Compute State Efficiency
    state_eff = compute_state_efficiency(all_records, tariff_inr=tariff, emission_factor_kg=factor)

    # 4. Detect Opportunities
    opps = opportunity_engine.evaluate_factory(records_by_machine, tariff_inr=tariff)

    # 5. Build Processed CSV
    # Each row is an interval evaluation across machines
    csv_rows = []
    for m_id, recs in records_by_machine.items():
        sorted_recs = sorted(recs, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_recs)):
            prev = sorted_recs[i - 1]
            curr = sorted_recs[i]
            dt = (curr.timestamp - prev.timestamp).total_seconds()
            if dt <= 0 or curr.energy_kwh is None or prev.energy_kwh is None or curr.energy_kwh < prev.energy_kwh:
                continue
            act_e = float(curr.energy_kwh - prev.energy_kwh)
            prod = int(curr.production_delta) if curr.production_delta else 0

            # Nominal expected interval energy based on state
            prof = DEFAULT_PROFILES.get(m_id)
            rated = prof.rated_power_kw if prof else 7.5
            state_val = curr.machine_state.value if hasattr(curr.machine_state, "value") else str(curr.machine_state)
            if state_val == "IDLE":
                exp_e = (rated * 0.18) * (dt / 3600.0)
            elif state_val == "SLEEP":
                exp_e = 0.35 * (dt / 3600.0)
            elif state_val == "RUNNING":
                exp_e = (rated * 0.85) * (dt / 3600.0)
            elif state_val == "DEGRADED":
                exp_e = (rated * 0.90) * (dt / 3600.0)
            else:
                exp_e = (rated * 0.85) * (dt / 3600.0)

            dev = act_e - exp_e
            pot_sav = max(0.0, dev)

            csv_rows.append({
                "timestamp": curr.timestamp.isoformat(),
                "machine_id": m_id,
                "machine_state": state_val,
                "dt_seconds": dt,
                "actual_energy_kwh": round(act_e, 6),
                "expected_energy_kwh": round(exp_e, 6),
                "deviation_kwh": round(dev, 6),
                "potential_savings_kwh": round(pot_sav, 6),
                "potential_savings_inr": round(pot_sav * tariff, 4),
                "potential_co2_savings_kg": round(pot_sav * factor, 6),
                "production_units": prod,
            })

    df_savings = pd.DataFrame(csv_rows)
    df_savings.to_csv(SAVINGS_CSV, index=False)
    print(f"Saved {len(df_savings)} rows to {SAVINGS_CSV}")

    # 6. Verification Example
    sample_verify = verify_savings(
        baseline_actual_energy_kwh=100.0,
        baseline_production_units=500.0,
        post_actual_energy_kwh=85.0,
        post_production_units=500.0,
        baseline_intervals=20,
        post_intervals=20,
        tariff_inr=tariff,
        emission_factor_kg=factor,
    )

    experiment_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 10 — Savings Estimation & Efficiency Analytics",
        "demonstration_tariff_inr_per_kwh": tariff,
        "demonstration_emission_factor_kg_per_kwh": factor,
        "factory_actual_energy_kwh": factory_eff["actual_energy_kwh"],
        "factory_expected_energy_kwh": factory_eff["expected_energy_kwh"],
        "factory_potential_savings_kwh": factory_eff["potential_savings_kwh"],
        "factory_potential_savings_inr": factory_eff["potential_savings_inr"],
        "factory_potential_co2_savings_kg": factory_eff["potential_co2_savings_kg"],
        "factory_actual_sec_kwh_per_unit": factory_eff["actual_sec_kwh_per_unit"],
        "factory_expected_sec_kwh_per_unit": factory_eff["expected_sec_kwh_per_unit"],
        "machine_savings_summary": machine_summaries,
        "state_efficiency_summary": state_eff,
        "opportunities_detected": opps,
        "example_verification": sample_verify,
        "reconciliation": {
            "sum_machine_actual_kwh": round(sum(m["actual_energy_kwh"] for m in machine_summaries), 6),
            "factory_actual_kwh": factory_eff["actual_energy_kwh"],
            "reconciliation_match": bool(np.isclose(
                sum(m["actual_energy_kwh"] for m in machine_summaries),
                factory_eff["actual_energy_kwh"],
                atol=1e-4,
            )),
        },
    }

    with open(SAVINGS_JSON, "w") as f:
        json.dump(experiment_results, f, indent=2)
    print(f"Saved experiment results to {SAVINGS_JSON}")


if __name__ == "__main__":
    generate_savings_artifacts()
