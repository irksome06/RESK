"""
Phase 10 Savings Estimation, Efficiency Analytics & Optimization Intelligence APIs.
Provides:
- GET /savings/factory
- GET /savings/machine/{machine_id}
- GET /savings/states
- POST /savings/verify
- GET /efficiency/factory
- GET /efficiency/machine/{machine_id}
- GET /optimization/opportunities
- GET /machines/{machine_id}/savings (legacy endpoint preserved)
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

from database.schemas import (
    TelemetryRecord,
    MachineState,
    FactorySavingsResponse,
    MachineSavingsResponse,
    StateSavingsItem,
    StateSavingsResponse,
    MachineEfficiencyResponse,
    FactoryEfficiencyResponse,
    SavingsVerificationRequest,
    SavingsVerificationResponse,
    OptimizationOpportunityItem,
    OptimizationOpportunitiesResponse,
)
from api.telemetry_store import telemetry_store
from simulator.machine_simulator import DEFAULT_PROFILES
from simulator.config import settings
from simulator.demo_state import demo_state
from analytics.savings import (
    compute_machine_savings,
    calculate_potential_savings,
    verify_savings,
    calculate_roi_payback,
)
from analytics.efficiency import (
    compute_machine_efficiency,
    compute_factory_efficiency,
    compute_state_efficiency,
)
from analytics.optimization import opportunity_engine

logger = logging.getLogger("api.savings")

router = APIRouter(tags=["Savings & Efficiency"])

RAW_TELEMETRY_CSV = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "raw",
    "factory_telemetry.csv",
)


def _get_telemetry_records(machine_id: Optional[str] = None, limit: int = 100) -> List[TelemetryRecord]:
    """Retrieves recent records from active demo state if active, store, or CSV fallback."""
    if demo_state.has_active_demo_data():
        recs = demo_state.get_demo_records(machine_id=machine_id)
        if len(recs) >= 2:
            return recs

    store_records = telemetry_store.get_recent(limit=limit, machine_id=machine_id)
    if store_records:
        return list(reversed(store_records))

    if os.path.exists(RAW_TELEMETRY_CSV):
        try:
            df = pd.read_csv(RAW_TELEMETRY_CSV)
            if machine_id:
                df = df[df["machine_id"] == machine_id]
            if len(df) == 0:
                return []
            df_tail = df.tail(limit)
            records: List[TelemetryRecord] = []
            for _, row in df_tail.iterrows():
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
                        source=str(row.get("source", "simulator")),
                    )
                    records.append(rec)
                except Exception:
                    continue
            return records
        except Exception as e:
            logger.warning("Could not read fallback telemetry CSV: %s", e)

    return []


# ==========================================
# 1. SAVINGS ENDPOINTS
# ==========================================

@router.get(
    "/savings/factory",
    response_model=FactorySavingsResponse,
    status_code=status.HTTP_200_OK,
)
def get_factory_savings(
    recent_intervals: int = Query(default=30, ge=2, le=500, description="Intervals per machine"),
    tariff_inr: Optional[float] = Query(default=None, description="Configurable demonstration tariff in INR/kWh"),
    emission_factor_kg: Optional[float] = Query(default=None, description="Configurable demonstration emission factor"),
):
    """
    Returns factory-wide aggregated potential and persistent savings opportunity.
    """
    tariff = tariff_inr or settings.ELECTRICITY_COST_INR_PER_KWH
    factor = emission_factor_kg or settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH
    machine_ids = list(DEFAULT_PROFILES.keys())

    tot_actual = 0.0
    tot_expected = 0.0
    tot_potential_savings_kwh = 0.0
    tot_persistent_opportunity_kwh = 0.0
    timestamps = []

    for m_id in machine_ids:
        recs = _get_telemetry_records(machine_id=m_id, limit=recent_intervals)
        if len(recs) >= 2:
            m_res = compute_machine_savings(recs, tariff_inr=tariff, emission_factor_kg=factor)
            tot_actual += m_res["actual_energy_kwh"]
            tot_expected += m_res["expected_energy_kwh"]
            tot_potential_savings_kwh += m_res["potential_savings_kwh"]
            tot_persistent_opportunity_kwh += m_res["persistent_opportunity_kwh"]
            timestamps.extend([recs[0].timestamp, recs[-1].timestamp])

    tot_actual = round(tot_actual, 6)
    tot_expected = round(tot_expected, 6)
    above_baseline = round(max(0.0, tot_actual - tot_expected), 6)
    tot_persistent_opportunity_kwh = round(tot_persistent_opportunity_kwh, 6)

    savings_rate_pct = round((above_baseline / tot_actual * 100.0), 2) if tot_actual > 1e-6 else 0.0
    baseline_gap_pct = (
        round(((tot_actual - tot_expected) / tot_expected * 100.0), 2)
        if tot_expected > 1e-6
        else 0.0
    )

    pot_savings_inr = round(tot_potential_savings_kwh * tariff, 2)
    pers_savings_inr = round(tot_persistent_opportunity_kwh * tariff, 2)
    pot_co2_kg = round(tot_potential_savings_kwh * factor, 4)
    pers_co2_kg = round(tot_persistent_opportunity_kwh * factor, 4)

    period_start = min(timestamps) if timestamps else None
    period_end = max(timestamps) if timestamps else None

    return FactorySavingsResponse(
        period_start=period_start,
        period_end=period_end,
        actual_energy_kwh=tot_actual,
        expected_energy_kwh=tot_expected,
        above_baseline_kwh=above_baseline,
        potential_savings_kwh=above_baseline,
        persistent_opportunity_kwh=tot_persistent_opportunity_kwh,
        savings_rate_pct=savings_rate_pct,
        baseline_gap_pct=baseline_gap_pct,
        potential_savings_inr=pot_savings_inr,
        persistent_savings_inr=pers_savings_inr,
        potential_co2_savings_kg=pot_co2_kg,
        persistent_co2_savings_kg=pers_co2_kg,
        tariff_inr_per_kwh=tariff,
        emission_factor_kg_per_kwh=factor,
        machine_count=len(machine_ids),
    )


@router.get(
    "/savings/machine/{machine_id}",
    response_model=MachineSavingsResponse,
    status_code=status.HTTP_200_OK,
)
def get_machine_savings_endpoint(
    machine_id: str,
    recent_intervals: int = Query(default=30, ge=2, le=500),
    tariff_inr: Optional[float] = Query(default=None),
    emission_factor_kg: Optional[float] = Query(default=None),
):
    """
    Returns machine-level potential and persistent savings opportunity.
    """
    clean_id = machine_id.strip().upper()
    known = set(DEFAULT_PROFILES.keys()) | set(telemetry_store.get_known_machine_ids())
    if clean_id not in known and not clean_id.startswith("M"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Machine '{machine_id}' not found.")

    recs = _get_telemetry_records(machine_id=clean_id, limit=recent_intervals)
    result = compute_machine_savings(
        records=recs,
        tariff_inr=tariff_inr,
        emission_factor_kg=emission_factor_kg,
    )
    result["machine_id"] = clean_id
    return MachineSavingsResponse(**result)


@router.get(
    "/savings/states",
    response_model=StateSavingsResponse,
    status_code=status.HTTP_200_OK,
)
def get_state_savings_endpoint(
    recent_intervals: int = Query(default=100, ge=5, le=1000),
    tariff_inr: Optional[float] = Query(default=None),
    emission_factor_kg: Optional[float] = Query(default=None),
):
    """
    Returns energy savings and deviation breakdown grouped by operational state.
    """
    recs = _get_telemetry_records(machine_id=None, limit=recent_intervals)
    states_dict = compute_state_efficiency(
        records=recs,
        tariff_inr=tariff_inr,
        emission_factor_kg=emission_factor_kg,
    )

    items: List[StateSavingsItem] = []
    tot_act = 0.0
    tot_exp = 0.0
    tot_dev = 0.0
    tot_pos_dev = 0.0
    tot_pot_inr = 0.0
    tot_pot_co2 = 0.0

    for s_name, item in states_dict.items():
        act = item["actual_energy_kwh"]
        exp = item["expected_energy_kwh"]
        dev = item["deviation_kwh"]
        pos_dev = item["positive_deviation_kwh"]
        pot_inr = item["potential_savings_inr"]
        pot_co2 = item["potential_co2_savings_kg"]

        tot_act += act
        tot_exp += exp
        tot_dev += dev
        tot_pos_dev += pos_dev
        tot_pot_inr += pot_inr
        tot_pot_co2 += pot_co2

        items.append(
            StateSavingsItem(
                machine_state=s_name,
                actual_energy_kwh=act,
                expected_energy_kwh=exp,
                deviation_kwh=dev,
                positive_deviation_kwh=pos_dev,
                potential_savings_kwh=pos_dev,
                potential_savings_inr=pot_inr,
                potential_co2_savings_kg=pot_co2,
                production_units=item["production_units"],
                sec_kwh_per_unit=item["sec_kwh_per_unit"],
            )
        )

    return StateSavingsResponse(
        total_actual_kwh=round(tot_act, 6),
        total_expected_kwh=round(tot_exp, 6),
        total_deviation_kwh=round(tot_dev, 6),
        total_positive_deviation_kwh=round(tot_pos_dev, 6),
        total_potential_savings_inr=round(tot_pot_inr, 2),
        total_potential_co2_savings_kg=round(tot_pot_co2, 4),
        states=items,
    )


# ==========================================
# 2. EFFICIENCY ENDPOINTS
# ==========================================

@router.get(
    "/efficiency/factory",
    response_model=FactoryEfficiencyResponse,
    status_code=status.HTTP_200_OK,
)
def get_factory_efficiency_endpoint(
    recent_intervals: int = Query(default=30, ge=2, le=500),
    tariff_inr: Optional[float] = Query(default=None),
    emission_factor_kg: Optional[float] = Query(default=None),
):
    """
    Returns aggregated factory production-normalized efficiency and SEC.
    """
    machine_ids = list(DEFAULT_PROFILES.keys())
    m_dict: Dict[str, List[TelemetryRecord]] = {}
    for m_id in machine_ids:
        m_dict[m_id] = _get_telemetry_records(machine_id=m_id, limit=recent_intervals)

    result = compute_factory_efficiency(
        machine_records_dict=m_dict,
        tariff_inr=tariff_inr,
        emission_factor_kg=emission_factor_kg,
    )

    machine_effs = [
        MachineEfficiencyResponse(
            machine_id=m["machine_id"],
            production_units=m["production_units"],
            actual_energy_kwh=m["actual_energy_kwh"],
            expected_energy_kwh=m["expected_energy_kwh"],
            actual_sec_kwh_per_unit=m["actual_sec_kwh_per_unit"],
            expected_sec_kwh_per_unit=m["expected_sec_kwh_per_unit"],
            sec_gap_kwh_per_unit=m["sec_gap_kwh_per_unit"],
            sec_improvement_pct=m["sec_improvement_pct"],
            potential_savings_kwh=m["potential_savings_kwh"],
            potential_savings_inr=m["potential_savings_inr"],
            potential_co2_savings_kg=m["potential_co2_savings_kg"],
            sample_count=m["sample_count"],
        )
        for m in result.get("machine_efficiencies", [])
    ]

    return FactoryEfficiencyResponse(
        production_units=result["production_units"],
        actual_energy_kwh=result["actual_energy_kwh"],
        expected_energy_kwh=result["expected_energy_kwh"],
        actual_sec_kwh_per_unit=result["actual_sec_kwh_per_unit"],
        expected_sec_kwh_per_unit=result["expected_sec_kwh_per_unit"],
        sec_gap_kwh_per_unit=result["sec_gap_kwh_per_unit"],
        sec_improvement_pct=None,
        potential_savings_kwh=result["potential_savings_kwh"],
        potential_savings_inr=result["potential_savings_inr"],
        potential_co2_savings_kg=result["potential_co2_savings_kg"],
        machine_count=result["machine_count"],
        machine_efficiencies=machine_effs,
    )


@router.get(
    "/efficiency/machine/{machine_id}",
    response_model=MachineEfficiencyResponse,
    status_code=status.HTTP_200_OK,
)
def get_machine_efficiency_endpoint(
    machine_id: str,
    recent_intervals: int = Query(default=30, ge=2, le=500),
    tariff_inr: Optional[float] = Query(default=None),
    emission_factor_kg: Optional[float] = Query(default=None),
):
    """
    Returns production-normalized efficiency and SEC for an individual machine.
    """
    clean_id = machine_id.strip().upper()
    known = set(DEFAULT_PROFILES.keys()) | set(telemetry_store.get_known_machine_ids())
    if clean_id not in known and not clean_id.startswith("M"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Machine '{machine_id}' not found.")

    recs = _get_telemetry_records(machine_id=clean_id, limit=recent_intervals)
    result = compute_machine_efficiency(
        records=recs,
        tariff_inr=tariff_inr,
        emission_factor_kg=emission_factor_kg,
    )
    result["machine_id"] = clean_id
    return MachineEfficiencyResponse(**result)


# ==========================================
# 3. SAVINGS VERIFICATION ENDPOINT
# ==========================================

@router.post(
    "/savings/verify",
    response_model=SavingsVerificationResponse,
    status_code=status.HTTP_200_OK,
)
def verify_savings_endpoint(request: SavingsVerificationRequest):
    """
    Verifies production-normalized energy savings comparing baseline and post-intervention periods.
    expected_post_energy = post_production * baseline_sec
    normalized_savings_kwh = max(0, expected_post_energy - post_actual_energy)
    """
    res = verify_savings(
        baseline_actual_energy_kwh=request.baseline_actual_energy_kwh,
        baseline_production_units=request.baseline_production_units,
        post_actual_energy_kwh=request.post_actual_energy_kwh,
        post_production_units=request.post_production_units,
        baseline_intervals=request.baseline_intervals,
        post_intervals=request.post_intervals,
        min_intervals=request.min_intervals,
        min_production_units=request.min_production_units,
        significance_threshold_pct=request.significance_threshold_pct,
        tariff_inr=request.tariff_inr,
        emission_factor_kg=request.emission_factor_kg,
    )

    # Calculate ROI payback if implementation cost supplied
    monthly_sav = round(res["estimated_savings_inr"] * 30.0, 2) if res["estimated_savings_inr"] > 0 else 0.0
    roi = calculate_roi_payback(
        monthly_savings_inr=monthly_sav,
        implementation_cost_inr=request.implementation_cost_inr,
    )

    res["payback_months"] = roi["payback_months"]
    res["annual_savings_inr"] = roi["annual_savings_inr"]

    return SavingsVerificationResponse(**res)


# ==========================================
# 4. OPTIMIZATION OPPORTUNITIES ENDPOINT
# ==========================================

@router.get(
    "/optimization/opportunities",
    response_model=OptimizationOpportunitiesResponse,
    status_code=status.HTTP_200_OK,
)
def get_optimization_opportunities(
    recent_intervals: int = Query(default=50, ge=5, le=500),
    tariff_inr: Optional[float] = Query(default=None),
):
    """
    Returns prioritized energy efficiency investigation opportunities across the factory.
    Opportunities are prioritized based strictly on energy-efficiency impact (NOT machine failure).
    """
    machine_ids = list(DEFAULT_PROFILES.keys())
    m_dict = {m_id: _get_telemetry_records(machine_id=m_id, limit=recent_intervals) for m_id in machine_ids}

    opps_raw = opportunity_engine.evaluate_factory(m_dict, tariff_inr=tariff_inr)
    items = [OptimizationOpportunityItem(**o) for o in opps_raw]

    high_pri_count = sum(1 for o in items if o.priority_level == "HIGH")
    total_annual = round(sum(o.estimated_annual_savings_inr for o in items), 2)

    return OptimizationOpportunitiesResponse(
        total_opportunities=len(items),
        high_priority_count=high_pri_count,
        total_estimated_annual_savings_inr=total_annual,
        opportunities=items,
    )


# ==========================================
# 5. LEGACY ENDPOINT (BACKWARD COMPATIBILITY)
# ==========================================

@router.get("/machines/{machine_id}/savings")
def get_legacy_machine_savings(machine_id: str):
    """
    Preserved legacy endpoint from Phase 5 for backwards compatibility.
    """
    recs = _get_telemetry_records(machine_id=machine_id.strip().upper(), limit=30)
    if len(recs) >= 2:
        res = compute_machine_savings(recs)
        return {
            "machine_id": machine_id,
            "energy_saved_kwh": res["potential_savings_kwh"],
            "cost_saved_inr": res["potential_savings_inr"],
            "co2_avoided_kg": res["potential_co2_savings_kg"],
        }
    return {
        "machine_id": machine_id,
        "energy_saved_kwh": 0.0,
        "cost_saved_inr": 0.0,
        "co2_avoided_kg": 0.0,
    }
