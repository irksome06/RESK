"""
Phase 10 Production-Normalized Efficiency & SEC Analytics.
Authoritative deterministic calculations for:
- Specific Energy Consumption (SEC = energy_kwh / production_units)
- Safe zero-production handling (returns None/null, never 0)
- Machine-level and factory-level production-normalized efficiency
- Operational state-level efficiency and opportunity breakdown
"""

from typing import List, Dict, Any, Optional
from database.schemas import TelemetryRecord, MachineState
from analytics.sec import calculate_sec
from simulator.config import settings
from analytics.deviation import compute_machine_deviation_from_records, analyze_state_deviations
from analytics.savings import calculate_potential_savings


def calculate_production_rate(production_units: float, time_span_hours: float) -> Optional[float]:
    """Preserved legacy rate calculator."""
    if time_span_hours <= 0:
        return None
    return round(production_units / time_span_hours, 2)


def calculate_utilization(runtime_sec: float, available_time_sec: float) -> float:
    """Preserved legacy utilization calculator."""
    if available_time_sec <= 0:
        return 0.0
    return round(min(1.0, max(0.0, runtime_sec / available_time_sec)) * 100.0, 2)


def compute_machine_efficiency(
    records: List[TelemetryRecord],
    tariff_inr: Optional[float] = None,
    emission_factor_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes production-normalized efficiency for an individual machine.
    Handles zero production by explicitly returning None/null for SEC.
    """
    if len(records) < 2:
        m_id = records[0].machine_id if records else "UNKNOWN"
        return {
            "machine_id": m_id,
            "production_units": 0,
            "actual_energy_kwh": 0.0,
            "expected_energy_kwh": 0.0,
            "actual_sec_kwh_per_unit": None,
            "expected_sec_kwh_per_unit": None,
            "sec_gap_kwh_per_unit": None,
            "sec_improvement_pct": None,
            "potential_savings_kwh": 0.0,
            "potential_savings_inr": 0.0,
            "potential_co2_savings_kg": 0.0,
            "sample_count": len(records),
        }

    dev_res = compute_machine_deviation_from_records(records)
    actual_kwh = dev_res["actual_energy_kwh"]
    expected_kwh = dev_res["expected_energy_kwh"]

    prod_deltas = [r.production_delta for r in records[1:] if r.production_delta is not None]
    total_prod = sum(prod_deltas) if prod_deltas else 0

    actual_sec = calculate_sec(actual_kwh, total_prod)
    expected_sec = calculate_sec(expected_kwh, total_prod)

    sec_gap = round(actual_sec - expected_sec, 4) if (actual_sec is not None and expected_sec is not None) else None

    # Improvement pct: (expected_sec - actual_sec) / expected_sec * 100
    if expected_sec is not None and expected_sec > 1e-6 and actual_sec is not None:
        sec_improvement = round(((expected_sec - actual_sec) / expected_sec) * 100.0, 2)
    else:
        sec_improvement = None

    savings = calculate_potential_savings(
        actual_energy_kwh=actual_kwh,
        expected_energy_kwh=expected_kwh,
        tariff_inr=tariff_inr,
        emission_factor_kg=emission_factor_kg,
    )

    return {
        "machine_id": dev_res["machine_id"],
        "production_units": total_prod,
        "actual_energy_kwh": actual_kwh,
        "expected_energy_kwh": expected_kwh,
        "actual_sec_kwh_per_unit": actual_sec,
        "expected_sec_kwh_per_unit": expected_sec,
        "sec_gap_kwh_per_unit": sec_gap,
        "sec_improvement_pct": sec_improvement,
        "potential_savings_kwh": savings["potential_savings_kwh"],
        "potential_savings_inr": savings["potential_savings_inr"],
        "potential_co2_savings_kg": savings["potential_co2_savings_kg"],
        "sample_count": len(records),
    }


def compute_factory_efficiency(
    machine_records_dict: Dict[str, List[TelemetryRecord]],
    tariff_inr: Optional[float] = None,
    emission_factor_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes factory-wide aggregated efficiency and SEC across all monitored machines.
    Reconciles machine actuals and expecteds.
    """
    total_actual = 0.0
    total_expected = 0.0
    total_prod = 0
    machines_eff = []

    for m_id, recs in machine_records_dict.items():
        m_eff = compute_machine_efficiency(
            recs,
            tariff_inr=tariff_inr,
            emission_factor_kg=emission_factor_kg,
        )
        machines_eff.append(m_eff)
        total_actual += m_eff["actual_energy_kwh"]
        total_expected += m_eff["expected_energy_kwh"]
        total_prod += m_eff["production_units"]

    total_actual = round(total_actual, 6)
    total_expected = round(total_expected, 6)

    factory_actual_sec = calculate_sec(total_actual, total_prod)
    factory_expected_sec = calculate_sec(total_expected, total_prod)

    sec_gap = (
        round(factory_actual_sec - factory_expected_sec, 4)
        if (factory_actual_sec is not None and factory_expected_sec is not None)
        else None
    )

    savings = calculate_potential_savings(
        actual_energy_kwh=total_actual,
        expected_energy_kwh=total_expected,
        tariff_inr=tariff_inr,
        emission_factor_kg=emission_factor_kg,
    )

    return {
        "production_units": total_prod,
        "actual_energy_kwh": total_actual,
        "expected_energy_kwh": total_expected,
        "actual_sec_kwh_per_unit": factory_actual_sec,
        "expected_sec_kwh_per_unit": factory_expected_sec,
        "sec_gap_kwh_per_unit": sec_gap,
        "potential_savings_kwh": savings["potential_savings_kwh"],
        "potential_savings_inr": savings["potential_savings_inr"],
        "potential_co2_savings_kg": savings["potential_co2_savings_kg"],
        "machine_count": len(machines_eff),
        "machine_efficiencies": machines_eff,
    }


def compute_state_efficiency(
    records: List[TelemetryRecord],
    tariff_inr: Optional[float] = None,
    emission_factor_kg: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Computes energy deviation, potential savings, and production per operating state.
    States: RUNNING, IDLE, SLEEP, DEGRADED, OVERLOAD.
    Does NOT label IDLE as waste or OVERLOAD as fault; reports measured deviation only.
    """
    dev_states = analyze_state_deviations(records)

    # Calculate production per state
    state_prod: Dict[str, int] = {s.value: 0 for s in MachineState}
    if len(records) >= 2:
        for r in records[1:]:
            s_val = r.machine_state.value if hasattr(r.machine_state, "value") else str(r.machine_state)
            if s_val in state_prod and r.production_delta is not None:
                state_prod[s_val] += int(r.production_delta)

    results: Dict[str, Dict[str, Any]] = {}
    for s_name, item in dev_states.items():
        act = item.get("actual_energy_kwh", 0.0)
        exp = item.get("expected_energy_kwh", 0.0)
        dev = item.get("deviation_kwh", 0.0)
        prod = state_prod.get(s_name, 0)

        savings = calculate_potential_savings(
            actual_energy_kwh=act,
            expected_energy_kwh=exp,
            tariff_inr=tariff_inr,
            emission_factor_kg=emission_factor_kg,
        )

        sec_val = calculate_sec(act, prod) if prod > 0 else None

        results[s_name] = {
            "machine_state": s_name,
            "actual_energy_kwh": round(act, 6),
            "expected_energy_kwh": round(exp, 6),
            "deviation_kwh": round(dev, 6),
            "positive_deviation_kwh": savings["potential_savings_kwh"],
            "potential_savings_kwh": savings["potential_savings_kwh"],
            "potential_savings_inr": savings["potential_savings_inr"],
            "potential_co2_savings_kg": savings["potential_co2_savings_kg"],
            "production_units": prod,
            "sec_kwh_per_unit": sec_val,
            "sample_count": item.get("sample_count", 0),
        }

    return results
