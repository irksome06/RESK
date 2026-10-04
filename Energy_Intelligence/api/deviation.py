"""
Phase 9 Energy Deviation & Intelligence API Endpoints.
Provides:
1. Machine-level energy deviation and persistent deviation detection.
2. Factory-level total energy deviation.
3. Machine contribution ranking for above-baseline factory consumption.
4. Operational state-level energy deviation breakdown.
"""

import os
import logging
from typing import List, Optional
from datetime import datetime, timezone
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

from database.schemas import (
    TelemetryRecord,
    MachineState,
    MachineDeviationStatusResponse,
    FactoryDeviationStatusResponse,
    DeviationContributor,
    FactoryContributorsResponse,
    StateDeviationItem,
    StateDeviationsResponse,
)
from api.telemetry_store import telemetry_store
from simulator.machine_simulator import DEFAULT_PROFILES
from analytics.deviation import (
    calculate_energy_deviation,
    compute_machine_deviation_from_records,
    analyze_state_deviations,
)
from analytics.persistence import persistence_detector
from analytics.contribution import compute_machine_contributions

logger = logging.getLogger("api.deviation")

router = APIRouter(prefix="/deviation", tags=["Deviation Intelligence"])

RAW_TELEMETRY_CSV = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "raw",
    "factory_telemetry.csv",
)


def _get_telemetry_records(machine_id: Optional[str] = None, limit: int = 100) -> List[TelemetryRecord]:
    """
    Retrieves recent telemetry records from live store, falling back to persisted CSV if empty.
    Returns records sorted chronologically.
    """
    # 1. Check live store
    store_records = telemetry_store.get_recent(limit=limit, machine_id=machine_id)
    if store_records:
        # store_records is newest first, reverse for chronological
        return list(reversed(store_records))

    # 2. Fallback to persisted raw telemetry CSV if available
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
                        source=str(row.get("source", "csv_history")),
                    )
                    records.append(rec)
                except Exception:
                    continue
            return records
        except Exception as e:
            logger.warning("Could not read fallback telemetry CSV: %s", e)

    return []


@router.get(
    "/machine/{machine_id}",
    response_model=MachineDeviationStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_machine_deviation(
    machine_id: str,
    recent_intervals: int = Query(default=20, ge=2, le=500, description="Number of recent intervals to evaluate"),
):
    """
    Computes energy deviation for an individual machine using the Phase 8.1 expected baseline.
    Evaluates persistent deviation using consecutive above-baseline intervals.
    """
    clean_id = machine_id.strip().upper()
    known = set(DEFAULT_PROFILES.keys()) | set(telemetry_store.get_known_machine_ids())
    if clean_id not in known and not clean_id.startswith("M"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id}' not found.",
        )

    records = _get_telemetry_records(machine_id=clean_id, limit=recent_intervals)
    if not records or len(records) < 2:
        return MachineDeviationStatusResponse(
            machine_id=clean_id,
            actual_energy_kwh=0.0,
            expected_energy_kwh=0.0,
            deviation_kwh=0.0,
            deviation_pct=0.0,
            status="NORMAL",
            persistent_intervals=0,
            interpretation="Insufficient recent telemetry observations to calculate deviation.",
        )

    dev_res = compute_machine_deviation_from_records(records)
    persist_res = persistence_detector.evaluate_intervals(dev_res.get("interval_deviations", []))

    final_status = persist_res["overall_status"]
    if final_status == "PERSISTENT_ABOVE_BASELINE":
        interpretation = (
            f"Machine {clean_id} exhibited {persist_res['current_consecutive_above']} consecutive "
            f"intervals with >{persist_res['threshold_pct']}% above-baseline consumption."
        )
    elif final_status == "ABOVE_BASELINE":
        interpretation = (
            f"Machine {clean_id} is consuming above expected baseline, but has not reached "
            f"the persistent alert threshold ({persist_res['consecutive_threshold']} consecutive intervals)."
        )
    elif final_status == "BELOW_BASELINE":
        interpretation = f"Machine {clean_id} is operating below expected baseline energy."
    else:
        interpretation = f"Machine {clean_id} energy consumption is operating within normal baseline limits."

    return MachineDeviationStatusResponse(
        machine_id=clean_id,
        actual_energy_kwh=dev_res["actual_energy_kwh"],
        expected_energy_kwh=dev_res["expected_energy_kwh"],
        deviation_kwh=dev_res["deviation_kwh"],
        deviation_pct=dev_res["deviation_pct"],
        status=final_status,
        persistent_intervals=persist_res["current_consecutive_above"],
        interpretation=interpretation,
    )


@router.get(
    "/factory",
    response_model=FactoryDeviationStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_factory_deviation(
    recent_intervals: int = Query(default=30, ge=2, le=500, description="Intervals per machine to evaluate"),
):
    """
    Returns aggregated factory-level energy deviation across all monitored machines.
    """
    machine_ids = list(DEFAULT_PROFILES.keys())
    tot_actual = 0.0
    tot_expected = 0.0
    active_count = 0

    for m_id in machine_ids:
        recs = _get_telemetry_records(machine_id=m_id, limit=recent_intervals)
        if len(recs) >= 2:
            res = compute_machine_deviation_from_records(recs)
            tot_actual += res["actual_energy_kwh"]
            tot_expected += res["expected_energy_kwh"]
            active_count += 1

    tot_actual = round(tot_actual, 6)
    tot_expected = round(tot_expected, 6)
    tot_deviation = round(tot_actual - tot_expected, 6)

    if tot_expected > 1e-6:
        dev_pct = round((tot_deviation / tot_expected) * 100.0, 2)
    else:
        dev_pct = 0.0

    if dev_pct > 15.0:
        f_status = "ABOVE_BASELINE"
    elif dev_pct < -15.0:
        f_status = "BELOW_BASELINE"
    else:
        f_status = "NORMAL"

    return FactoryDeviationStatusResponse(
        factory_actual_energy_kwh=tot_actual,
        factory_expected_energy_kwh=tot_expected,
        factory_deviation_kwh=tot_deviation,
        factory_deviation_pct=dev_pct,
        status=f_status,
        machine_count=active_count,
    )


@router.get(
    "/contributors",
    response_model=FactoryContributorsResponse,
    status_code=status.HTTP_200_OK,
)
def get_factory_contributors(
    recent_intervals: int = Query(default=30, ge=2, le=500, description="Intervals per machine to evaluate"),
):
    """
    Ranks machines by their percentage contribution to positive factory-level energy deviation.
    """
    machine_ids = list(DEFAULT_PROFILES.keys())
    machine_deviations = []

    for m_id in machine_ids:
        recs = _get_telemetry_records(machine_id=m_id, limit=recent_intervals)
        if len(recs) >= 2:
            res = compute_machine_deviation_from_records(recs)
            machine_deviations.append(res)
        else:
            machine_deviations.append({
                "machine_id": m_id,
                "actual_energy_kwh": 0.0,
                "expected_energy_kwh": 0.0,
                "deviation_kwh": 0.0,
                "deviation_pct": 0.0,
            })

    result = compute_machine_contributions(machine_deviations)

    contributors = [
        DeviationContributor(
            machine_id=c["machine_id"],
            actual_energy_kwh=c["actual_energy_kwh"],
            expected_energy_kwh=c["expected_energy_kwh"],
            deviation_kwh=c["deviation_kwh"],
            deviation_pct=c["deviation_pct"],
            contribution_pct=c["contribution_pct"],
        )
        for c in result.get("contributors", [])
    ]

    return FactoryContributorsResponse(
        factory_deviation_kwh=result["factory_deviation_kwh"],
        total_positive_factory_deviation=result["total_positive_deviation_kwh"],
        contributors=contributors,
    )


@router.get(
    "/states",
    response_model=StateDeviationsResponse,
    status_code=status.HTTP_200_OK,
)
def get_state_deviations(
    recent_intervals: int = Query(default=100, ge=5, le=1000, description="Total records to evaluate"),
):
    """
    Calculates energy deviation breakdown across machine operational states
    (RUNNING, IDLE, SLEEP, DEGRADED, OVERLOAD).
    """
    records = _get_telemetry_records(machine_id=None, limit=recent_intervals)

    state_dict = analyze_state_deviations(records)

    items: List[StateDeviationItem] = []
    tot_act = 0.0
    tot_exp = 0.0

    for state_name, val in state_dict.items():
        act = val.get("actual_energy_kwh", 0.0)
        exp = val.get("expected_energy_kwh", 0.0)
        dev = val.get("deviation_kwh", 0.0)
        dev_pct = val.get("deviation_pct", 0.0)

        tot_act += act
        tot_exp += exp

        items.append(
            StateDeviationItem(
                state=state_name,
                actual_energy_kwh=round(act, 6),
                expected_energy_kwh=round(exp, 6),
                deviation_kwh=round(dev, 6),
                deviation_pct=round(dev_pct, 2),
            )
        )

    tot_dev = round(tot_act - tot_exp, 6)

    return StateDeviationsResponse(
        total_actual_kwh=round(tot_act, 6),
        total_expected_kwh=round(tot_exp, 6),
        total_deviation_kwh=tot_dev,
        states=items,
    )
