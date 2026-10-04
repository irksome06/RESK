"""
Phase 10 Savings Estimation, Verification & Financial Impact Engine.
Authoritative deterministic calculations for:
- Gross above-baseline energy vs persistent above-baseline savings opportunity
- Cost (INR) and CO2 (kg) avoidance using configurable demonstration factors
- Production-normalized savings verification (IPMVP-inspired normalized verification)
- Verification statuses: NO_BASELINE, INSUFFICIENT_DATA, NO_IMPROVEMENT, IMPROVEMENT_DETECTED, SAVINGS_VERIFIED
- ROI and payback horizon calculations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from simulator.config import settings
from analytics.sec import calculate_sec
from database.schemas import TelemetryRecord, MachineState
from analytics.deviation import compute_machine_deviation_from_records
from analytics.persistence import persistence_detector


def calculate_savings(
    baseline_kwh: float,
    actual_kwh: float,
    tariff_inr: float = 8.00,
    emission_factor_kg: float = 0.716,
) -> Dict[str, float]:
    """
    Preserved legacy interface from Phase 7/8.
    Calculates simple energy, cost, and CO2 reduction against baseline.
    """
    energy_saved = max(0.0, baseline_kwh - actual_kwh)
    cost_saved = round(energy_saved * tariff_inr, 2)
    co2_avoided = round(energy_saved * emission_factor_kg, 4)
    pct_reduction = round((energy_saved / baseline_kwh * 100.0), 2) if baseline_kwh > 0 else 0.0

    return {
        "energy_saved_kwh": round(energy_saved, 4),
        "percentage_reduction": pct_reduction,
        "cost_saved_inr": cost_saved,
        "co2_avoided_kg": co2_avoided,
    }


def calculate_potential_savings(
    actual_energy_kwh: float,
    expected_energy_kwh: float,
    is_persistent: bool = False,
    tariff_inr: Optional[float] = None,
    emission_factor_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes deterministic potential energy savings for an interval or period.
    Rules:
    - potential_savings_kwh = max(0, actual_energy_kwh - expected_energy_kwh) (clamped at 0, no negative savings)
    - persistent_savings_kwh = potential_savings_kwh if is_persistent else 0.0
    - savings_rate_pct = potential_savings_kwh / actual_energy_kwh * 100 (safe zero handling)
    - baseline_gap_pct = (actual - expected) / expected * 100 (safe zero handling)
    - Cost and CO2 calculated using configurable demonstration assumptions.
    """
    actual = max(0.0, float(actual_energy_kwh))
    expected = max(0.0, float(expected_energy_kwh))
    tariff = float(tariff_inr if tariff_inr is not None else settings.ELECTRICITY_COST_INR_PER_KWH)
    emission_factor = float(emission_factor_kg if emission_factor_kg is not None else settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH)

    deviation_kwh = round(actual - expected, 6)
    potential_savings_kwh = round(max(0.0, deviation_kwh), 6)
    persistent_savings_kwh = round(potential_savings_kwh if is_persistent else 0.0, 6)

    # Safe rates
    savings_rate_pct = round((potential_savings_kwh / actual * 100.0), 2) if actual > 1e-6 else 0.0
    baseline_gap_pct = round((deviation_kwh / expected * 100.0), 2) if expected > 1e-6 else (100.0 if actual > 0 else 0.0)

    # Financial and CO2 impact
    potential_savings_inr = round(potential_savings_kwh * tariff, 2)
    persistent_savings_inr = round(persistent_savings_kwh * tariff, 2)
    potential_co2_kg = round(potential_savings_kwh * emission_factor, 4)
    persistent_co2_kg = round(persistent_savings_kwh * emission_factor, 4)

    return {
        "actual_energy_kwh": round(actual, 6),
        "expected_energy_kwh": round(expected, 6),
        "deviation_kwh": deviation_kwh,
        "potential_savings_kwh": potential_savings_kwh,
        "persistent_opportunity_kwh": persistent_savings_kwh,
        "savings_rate_pct": savings_rate_pct,
        "baseline_gap_pct": baseline_gap_pct,
        "potential_savings_inr": potential_savings_inr,
        "persistent_savings_inr": persistent_savings_inr,
        "potential_co2_savings_kg": potential_co2_kg,
        "persistent_co2_savings_kg": persistent_co2_kg,
        "tariff_inr_per_kwh": tariff,
        "emission_factor_kg_per_kwh": emission_factor,
        "tariff_label": "Configurable demonstration tariff",
        "emission_factor_label": "Configurable demonstration grid emission factor",
    }


def calculate_roi_payback(
    monthly_savings_inr: float,
    implementation_cost_inr: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculates annualized savings and simple financial payback horizon in months.
    Rules:
    - annual_savings_inr = monthly_savings_inr * 12
    - payback_months = implementation_cost_inr / monthly_savings_inr
    - If implementation_cost_inr is missing/negative or monthly_savings_inr <= 0, payback_months is None.
    - Never fabricates or hallucinates implementation costs.
    """
    monthly = max(0.0, float(monthly_savings_inr))
    annual_savings = round(monthly * 12.0, 2)

    if implementation_cost_inr is not None and implementation_cost_inr >= 0 and monthly > 1e-4:
        payback_months = round(float(implementation_cost_inr) / monthly, 2)
    else:
        payback_months = None

    return {
        "monthly_savings_inr": round(monthly, 2),
        "annual_savings_inr": annual_savings,
        "implementation_cost_inr": round(float(implementation_cost_inr), 2) if implementation_cost_inr is not None else None,
        "payback_months": payback_months,
    }


def verify_savings(
    baseline_actual_energy_kwh: float,
    baseline_production_units: float,
    post_actual_energy_kwh: float,
    post_production_units: float,
    baseline_intervals: int = 10,
    post_intervals: int = 10,
    min_intervals: int = 5,
    min_production_units: float = 1.0,
    significance_threshold_pct: float = 2.0,
    tariff_inr: Optional[float] = None,
    emission_factor_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Production-normalized energy savings verification methodology.
    Compares baseline period to post-intervention period normalized by production output:
    expected_post_energy = post_production * baseline_sec
    normalized_savings_kwh = max(0, expected_post_energy - post_actual_energy)
    sec_improvement_pct = (baseline_sec - post_sec) / baseline_sec * 100

    Verification Statuses:
    - NO_BASELINE: Baseline energy or production is zero or negative.
    - INSUFFICIENT_DATA: Observation intervals or post-production below minimum requirements.
    - NO_IMPROVEMENT: Post-intervention SEC is greater than or equal to baseline SEC.
    - IMPROVEMENT_DETECTED: SEC improved, but below the significant verification threshold.
    - SAVINGS_VERIFIED: SEC improved by >= significance_threshold_pct with verified production.

    Assumptions Documented:
    Assumes baseline SEC remains a valid reference standard for the post-intervention operational regime.
    Not an accredited IPMVP protocol; provides transparent engineering verification.
    """
    tariff = float(tariff_inr if tariff_inr is not None else settings.ELECTRICITY_COST_INR_PER_KWH)
    emission_factor = float(emission_factor_kg if emission_factor_kg is not None else settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH)

    # 1. Baseline Availability Guard
    if baseline_actual_energy_kwh <= 0 or baseline_production_units <= 0:
        return {
            "status": "NO_BASELINE",
            "message": "Baseline energy or production is missing or non-positive.",
            "baseline_sec": None,
            "post_sec": None,
            "sec_improvement_pct": None,
            "expected_post_energy_kwh": None,
            "post_actual_energy_kwh": post_actual_energy_kwh,
            "normalized_savings_kwh": 0.0,
            "estimated_savings_inr": 0.0,
            "estimated_co2_savings_kg": 0.0,
            "tariff_inr_per_kwh": tariff,
            "emission_factor_kg_per_kwh": emission_factor,
        }

    # 2. Data Sufficiency Guard
    if (
        baseline_intervals < min_intervals
        or post_intervals < min_intervals
        or post_production_units < min_production_units
        or post_actual_energy_kwh <= 0
    ):
        b_sec = round(baseline_actual_energy_kwh / baseline_production_units, 4)
        p_sec = round(post_actual_energy_kwh / post_production_units, 4) if post_production_units > 0 else None
        return {
            "status": "INSUFFICIENT_DATA",
            "message": f"Insufficient sample intervals (min required: {min_intervals}) or insufficient post production.",
            "baseline_sec": b_sec,
            "post_sec": p_sec,
            "sec_improvement_pct": None,
            "expected_post_energy_kwh": None,
            "post_actual_energy_kwh": post_actual_energy_kwh,
            "normalized_savings_kwh": 0.0,
            "estimated_savings_inr": 0.0,
            "estimated_co2_savings_kg": 0.0,
            "tariff_inr_per_kwh": tariff,
            "emission_factor_kg_per_kwh": emission_factor,
        }

    # 3. Production-Normalized Calculation
    baseline_sec = baseline_actual_energy_kwh / baseline_production_units
    post_sec = post_actual_energy_kwh / post_production_units

    sec_improvement_pct = round(((baseline_sec - post_sec) / baseline_sec) * 100.0, 2)
    expected_post_energy = round(post_production_units * baseline_sec, 6)
    raw_diff = expected_post_energy - post_actual_energy_kwh
    normalized_savings_kwh = round(max(0.0, raw_diff), 6)

    # 4. Status Determination
    if sec_improvement_pct <= 0.0 or normalized_savings_kwh <= 0.0:
        status = "NO_IMPROVEMENT"
        msg = f"Post-intervention SEC ({round(post_sec, 4)}) is higher or equal to baseline SEC ({round(baseline_sec, 4)})."
    elif sec_improvement_pct < significance_threshold_pct:
        status = "IMPROVEMENT_DETECTED"
        msg = f"SEC improved by {sec_improvement_pct}%, but below the {significance_threshold_pct}% verification threshold."
    else:
        status = "SAVINGS_VERIFIED"
        msg = f"Verified savings achieved with {sec_improvement_pct}% reduction in Specific Energy Consumption."

    savings_inr = round(normalized_savings_kwh * tariff, 2)
    co2_saved = round(normalized_savings_kwh * emission_factor, 4)

    return {
        "status": status,
        "message": msg,
        "baseline_sec": round(baseline_sec, 4),
        "post_sec": round(post_sec, 4),
        "sec_improvement_pct": sec_improvement_pct,
        "expected_post_energy_kwh": expected_post_energy,
        "post_actual_energy_kwh": round(post_actual_energy_kwh, 6),
        "normalized_savings_kwh": normalized_savings_kwh,
        "estimated_savings_inr": savings_inr,
        "estimated_co2_savings_kg": co2_saved,
        "tariff_inr_per_kwh": tariff,
        "emission_factor_kg_per_kwh": emission_factor,
        "assumptions": (
            "Assumes baseline Specific Energy Consumption (kWh/unit) reflects the expected "
            "production performance standard. Not an accredited IPMVP protocol."
        ),
    }


def compute_machine_savings(
    records: List[TelemetryRecord],
    tariff_inr: Optional[float] = None,
    emission_factor_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes cumulative potential savings, persistent opportunity, SEC, and economic impact
    for an individual machine based on its historical telemetry records.
    """
    if len(records) < 2:
        m_id = records[0].machine_id if records else "UNKNOWN"
        return {
            "machine_id": m_id,
            "actual_energy_kwh": 0.0,
            "expected_energy_kwh": 0.0,
            "deviation_kwh": 0.0,
            "potential_savings_kwh": 0.0,
            "persistent_opportunity_kwh": 0.0,
            "savings_rate_pct": 0.0,
            "baseline_gap_pct": 0.0,
            "potential_savings_inr": 0.0,
            "persistent_savings_inr": 0.0,
            "potential_co2_savings_kg": 0.0,
            "persistent_co2_savings_kg": 0.0,
            "total_production_units": 0,
            "actual_sec_kwh_per_unit": None,
            "expected_sec_kwh_per_unit": None,
            "sec_gap_kwh_per_unit": None,
            "status": "INSUFFICIENT_DATA",
            "tariff_inr_per_kwh": tariff_inr or settings.ELECTRICITY_COST_INR_PER_KWH,
            "emission_factor_kg_per_kwh": emission_factor_kg or settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH,
        }

    dev_res = compute_machine_deviation_from_records(records)
    persist_res = persistence_detector.evaluate_intervals(dev_res.get("interval_deviations", []))
    is_persistent = persist_res["is_persistent"]

    actual_kwh = dev_res["actual_energy_kwh"]
    expected_kwh = dev_res["expected_energy_kwh"]

    savings_calc = calculate_potential_savings(
        actual_energy_kwh=actual_kwh,
        expected_energy_kwh=expected_kwh,
        is_persistent=is_persistent,
        tariff_inr=tariff_inr,
        emission_factor_kg=emission_factor_kg,
    )

    # Compute production units
    prod_deltas = [r.production_delta for r in records[1:] if r.production_delta is not None]
    total_prod = sum(prod_deltas) if prod_deltas else 0

    actual_sec = calculate_sec(actual_kwh, total_prod)
    expected_sec = calculate_sec(expected_kwh, total_prod)
    sec_gap = round(actual_sec - expected_sec, 4) if (actual_sec is not None and expected_sec is not None) else None

    savings_calc["machine_id"] = dev_res["machine_id"]
    savings_calc["total_production_units"] = total_prod
    savings_calc["actual_sec_kwh_per_unit"] = actual_sec
    savings_calc["expected_sec_kwh_per_unit"] = expected_sec
    savings_calc["sec_gap_kwh_per_unit"] = sec_gap
    savings_calc["deviation_status"] = persist_res["overall_status"]
    savings_calc["persistent_intervals"] = persist_res["current_consecutive_above"]

    return savings_calc
