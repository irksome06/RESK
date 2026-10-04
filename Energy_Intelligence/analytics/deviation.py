"""
Phase 9 Energy Deviation Analytics.
Computes authoritative energy deviation metrics comparing actual energy vs Phase 8.1 expected baseline:
- deviation_kwh = actual_energy - expected_energy
- deviation_pct = (actual_energy - expected_energy) / expected_energy * 100
- Operational state-level energy deviation breakdown
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

from database.schemas import TelemetryRecord, MachineState
from ml.baseline import baseline_service, EnergyBaselineService


def calculate_energy_deviation(
    actual_energy_kwh: float,
    expected_energy_kwh: float,
) -> Dict[str, Any]:
    """
    Computes deterministic energy deviation between actual and expected energy.

    Args:
        actual_energy_kwh: Measured actual electrical energy consumption in kWh
        expected_energy_kwh: Predicted baseline expected energy in kWh

    Returns:
        Dict with actual, expected, deviation_kwh, deviation_pct, is_above_baseline, status.
    """
    actual = max(0.0, float(actual_energy_kwh))
    expected = max(0.0, float(expected_energy_kwh))
    deviation_kwh = round(actual - expected, 6)

    if expected > 1e-6:
        deviation_pct = round((deviation_kwh / expected) * 100.0, 2)
    else:
        deviation_pct = 0.0 if abs(deviation_kwh) < 1e-6 else (100.0 if actual > 0 else 0.0)

    # Classification threshold: +/- 5% default nominal tolerance
    if deviation_pct > 15.0:
        dev_status = "ABOVE_BASELINE"
    elif deviation_pct < -15.0:
        dev_status = "BELOW_BASELINE"
    else:
        dev_status = "NORMAL"

    return {
        "actual_energy_kwh": round(actual, 6),
        "expected_energy_kwh": round(expected, 6),
        "deviation_kwh": deviation_kwh,
        "deviation_pct": deviation_pct,
        "is_above_baseline": deviation_kwh > 0.0,
        "status": dev_status,
    }


def compute_machine_deviation_from_records(
    records: List[TelemetryRecord],
    service: Optional[EnergyBaselineService] = None,
) -> Dict[str, Any]:
    """
    Computes cumulative actual vs expected energy and deviation over a sequence of telemetry records
    for a single machine using the Phase 8.1 retrospective production-aware baseline.
    """
    if service is None:
        service = baseline_service

    if len(records) < 2:
        return {
            "machine_id": records[0].machine_id if records else "UNKNOWN",
            "actual_energy_kwh": 0.0,
            "expected_energy_kwh": 0.0,
            "deviation_kwh": 0.0,
            "deviation_pct": 0.0,
            "status": "INSUFFICIENT_DATA",
            "sample_count": len(records),
        }

    # Sort strictly by timestamp
    sorted_recs = sorted(records, key=lambda r: r.timestamp)
    machine_id = sorted_recs[0].machine_id

    total_actual = 0.0
    total_expected = 0.0
    interval_deviations: List[Dict[str, Any]] = []

    for i in range(1, len(sorted_recs)):
        prev = sorted_recs[i - 1]
        curr = sorted_recs[i]

        dt = (curr.timestamp - prev.timestamp).total_seconds()
        if dt <= 0 or dt > 30.0:  # Exclude non-monotonic intervals or cross-session gaps
            continue

        # Actual interval energy
        e_curr = curr.energy_kwh
        e_prev = prev.energy_kwh
        if e_curr is None or e_prev is None or e_curr < e_prev:
            continue  # Exclude non-monotonic intervals / meter drops

        act_interval = float(e_curr - e_prev)
        # Physical consistency check: implied power cannot exceed 100 kW (max machine rated power is 25 kW)
        if dt > 0 and (act_interval * 3600.0 / dt) > 100.0:
            continue

        # Baseline expected energy input features (Phase 8.1 V2)
        prod_delta = curr.production_delta if curr.production_delta is not None else 0
        prod_rate = round(float(prod_delta) / (dt / 3600.0), 2) if dt > 0 else 0.0

        state_val = curr.machine_state.value if hasattr(curr.machine_state, "value") else str(curr.machine_state)

        feat_dict = {
            "machine_id": machine_id,
            "machine_state": state_val,
            "production_delta": prod_delta,
            "production_rate": prod_rate,
            "rpm": float(curr.rpm) if curr.rpm is not None else 1450.0,
            "torque_nm": float(curr.torque_nm) if curr.torque_nm is not None else 0.0,
            "temperature_c": float(curr.temperature_c) if curr.temperature_c is not None else 50.0,
            "vibration": float(curr.vibration) if curr.vibration is not None else 0.18,
            "health_score": float(curr.health_score) if curr.health_score is not None else 100.0,
            "anomaly_score": float(curr.anomaly_score) if curr.anomaly_score is not None else 0.0,
            "hour_of_day": float(curr.timestamp.hour),
            "day_of_week": float(curr.timestamp.weekday()),
            "dt_seconds": float(dt),
        }

        baseline_res = service.predict_expected_energy(feat_dict)
        exp_interval = float(baseline_res["expected_energy_kwh"])

        total_actual += act_interval
        total_expected += exp_interval

        dev_res = calculate_energy_deviation(act_interval, exp_interval)
        dev_res["timestamp"] = curr.timestamp.isoformat()
        dev_res["machine_state"] = state_val
        interval_deviations.append(dev_res)

    dev_summary = calculate_energy_deviation(total_actual, total_expected)
    dev_summary["machine_id"] = machine_id
    dev_summary["sample_count"] = len(interval_deviations)
    dev_summary["interval_deviations"] = interval_deviations

    return dev_summary


def analyze_state_deviations(
    records: List[TelemetryRecord],
    service: Optional[EnergyBaselineService] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregates energy deviation grouped by machine operational state
    (RUNNING, IDLE, SLEEP, DEGRADED, OVERLOAD).

    Answers: "How much did each operational state consume above/below its expected baseline?"
    """
    if service is None:
        service = baseline_service

    state_actuals: Dict[str, float] = {s.value: 0.0 for s in MachineState}
    state_expecteds: Dict[str, float] = {s.value: 0.0 for s in MachineState}
    state_counts: Dict[str, int] = {s.value: 0 for s in MachineState}

    if len(records) < 2:
        return {
            s.value: {
                "machine_state": s.value,
                "actual_energy_kwh": 0.0,
                "expected_energy_kwh": 0.0,
                "deviation_kwh": 0.0,
                "deviation_pct": 0.0,
                "status": "NORMAL",
                "sample_count": 0,
            }
            for s in MachineState
        }

    # Group by machine first to preserve per-machine interval monotonicity
    machine_groups: Dict[str, List[TelemetryRecord]] = {}
    for r in records:
        machine_groups.setdefault(r.machine_id, []).append(r)

    for m_id, m_records in machine_groups.items():
        sorted_m = sorted(m_records, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_m)):
            prev = sorted_m[i - 1]
            curr = sorted_m[i]

            dt = (curr.timestamp - prev.timestamp).total_seconds()
            if dt <= 0 or dt > 30.0:  # Exclude non-monotonic intervals or cross-session gaps
                continue

            e_curr = curr.energy_kwh
            e_prev = prev.energy_kwh
            if e_curr is None or e_prev is None or e_curr < e_prev:
                continue

            act_interval = float(e_curr - e_prev)
            # Physical consistency check: implied power cannot exceed 100 kW
            if dt > 0 and (act_interval * 3600.0 / dt) > 100.0:
                continue
            prod_delta = curr.production_delta if curr.production_delta is not None else 0
            prod_rate = round(float(prod_delta) / (dt / 3600.0), 2) if dt > 0 else 0.0
            state_val = curr.machine_state.value if hasattr(curr.machine_state, "value") else str(curr.machine_state)

            feat_dict = {
                "machine_id": m_id,
                "machine_state": state_val,
                "production_delta": prod_delta,
                "production_rate": prod_rate,
                "rpm": float(curr.rpm) if curr.rpm is not None else 1450.0,
                "torque_nm": float(curr.torque_nm) if curr.torque_nm is not None else 0.0,
                "temperature_c": float(curr.temperature_c) if curr.temperature_c is not None else 50.0,
                "vibration": float(curr.vibration) if curr.vibration is not None else 0.18,
                "health_score": float(curr.health_score) if curr.health_score is not None else 100.0,
                "anomaly_score": float(curr.anomaly_score) if curr.anomaly_score is not None else 0.0,
                "hour_of_day": float(curr.timestamp.hour),
                "day_of_week": float(curr.timestamp.weekday()),
                "dt_seconds": float(dt),
            }

            exp_interval = float(service.predict_expected_energy(feat_dict)["expected_energy_kwh"])

            if state_val in state_actuals:
                state_actuals[state_val] += act_interval
                state_expecteds[state_val] += exp_interval
                state_counts[state_val] += 1

    results: Dict[str, Dict[str, Any]] = {}
    for state_name in state_actuals:
        act = state_actuals[state_name]
        exp = state_expecteds[state_name]
        dev_res = calculate_energy_deviation(act, exp)
        dev_res["machine_state"] = state_name
        dev_res["sample_count"] = state_counts[state_name]
        results[state_name] = dev_res

    return results
