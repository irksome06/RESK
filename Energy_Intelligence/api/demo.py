"""
Phase 12 Unified Factory Demonstration API Endpoints.
Composes deterministic analytics, production-aware baselines, forecasting,
savings, efficiency, and optimization intelligence into unified demo snapshots.
Endpoints:
- GET /demo/status: Live demo execution state and pipeline health
- GET /demo/factory: Unified factory-level intelligence snapshot
- GET /demo/machine/{machine_id}: Unified machine-level intelligence profile
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

from database.schemas import (
    TelemetryRecord,
    MachineState,
    DemoStatusResponse,
    DemoFactorySnapshotResponse,
    DemoMachineDetailResponse,
)
from simulator.config import settings
from simulator.machine_simulator import DEFAULT_PROFILES
from simulator.demo_state import demo_state
from api.telemetry_store import telemetry_store
from analytics.savings import compute_machine_savings, calculate_potential_savings
from analytics.efficiency import compute_machine_efficiency, compute_factory_efficiency
from analytics.deviation import compute_machine_deviation_from_records, calculate_energy_deviation
from analytics.optimization import opportunity_engine
from ml.forecasting import forecasting_service

logger = logging.getLogger("api.demo")

router = APIRouter(prefix="/demo", tags=["Factory Demo"])

RAW_TELEMETRY_CSV = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "raw",
    "factory_telemetry.csv",
)


def _load_demo_telemetry(machine_id: Optional[str] = None, limit: int = 100) -> List[TelemetryRecord]:
    """
    Retrieves telemetry records from authoritative demo state if active,
    otherwise falling back to live store or persisted raw CSV.
    Guarantees chronological ordering and filters out cross-session gaps.
    """
    if demo_state.has_active_demo_data():
        recs = demo_state.get_demo_records(machine_id=machine_id)
        if len(recs) >= 2:
            return recs

    store_records = telemetry_store.get_recent(limit=limit, machine_id=machine_id)
    if store_records and len(store_records) >= 2:
        recs = list(reversed(store_records))
        # Filter for contiguous, monotonic session without large gaps
        filtered = [recs[0]]
        for r in recs[1:]:
            dt = (r.timestamp - filtered[-1].timestamp).total_seconds()
            if 0 < dt <= 30.0 and r.energy_kwh >= filtered[-1].energy_kwh:
                filtered.append(r)
        if len(filtered) >= 2:
            return filtered

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
            logger.warning("Error reading fallback CSV in demo API: %s", e)

    return []


@router.get("/status", response_model=DemoStatusResponse)
def get_demo_status():
    """
    Returns live demonstration status, elapsed run time, scenario phase,
    telemetry count, and subsystem connectivity.
    """
    return demo_state.get_status()


@router.get("/factory", response_model=DemoFactorySnapshotResponse)
def get_demo_factory():
    """
    Returns a unified snapshot of the factory combining:
    - Production and energy metrics
    - Factory SEC (Specific Energy Consumption)
    - Production-aware baseline and deviation
    - Multi-step energy forecast
    - Potential and verified savings
    - Prioritized optimization opportunities
    - Machine status overview
    """
    all_machine_ids = sorted(list(DEFAULT_PROFILES.keys()))
    machine_records_dict: Dict[str, List[TelemetryRecord]] = {}

    for m_id in all_machine_ids:
        machine_records_dict[m_id] = _load_demo_telemetry(machine_id=m_id, limit=60)

    if not demo_state.has_active_demo_data():
        flat = []
        for r_list in machine_records_dict.values():
            flat.extend(r_list)
        if flat:
            demo_state.set_active_demo_records(flat)

    # 1. Savings & Baseline calculations per machine
    total_actual_energy = 0.0
    total_expected_energy = 0.0
    total_potential_savings_kwh = 0.0
    total_potential_savings_inr = 0.0
    total_potential_co2_kg = 0.0
    total_production_units = 0
    machine_status_list = []
    latest_ts = datetime.now(timezone.utc)

    for m_id in all_machine_ids:
        recs = machine_records_dict[m_id]
        profile = DEFAULT_PROFILES.get(m_id)
        name = profile.name if profile else m_id

        if recs:
            latest_rec = recs[-1]
            latest_ts = max(latest_ts, latest_rec.timestamp)
            current_state = latest_rec.machine_state.value if hasattr(latest_rec.machine_state, "value") else str(latest_rec.machine_state)
            current_power = round(latest_rec.power_kw, 2)
            current_energy = round(latest_rec.energy_kwh, 4)
            current_prod = int(latest_rec.production_count or 0)
            health = round(latest_rec.health_score or 100.0, 1)

            # Machine savings summary
            m_savings = compute_machine_savings(recs, tariff_inr=settings.ELECTRICITY_TARIFF_INR_PER_KWH)
            m_eff = compute_machine_efficiency(recs)

            total_actual_energy += m_savings["actual_energy_kwh"]
            total_expected_energy += m_savings["expected_energy_kwh"]
            total_potential_savings_kwh += m_savings["potential_savings_kwh"]
            total_potential_savings_inr += m_savings["potential_savings_inr"]
            total_potential_co2_kg += m_savings.get("potential_co2_savings_kg", m_savings.get("potential_co2_kg", 0.0))
            total_production_units += m_eff["production_units"]

            machine_status_list.append({
                "machine_id": m_id,
                "name": name,
                "state": current_state,
                "power_kw": current_power,
                "energy_kwh": m_savings["actual_energy_kwh"],
                "actual_energy_kwh": m_savings["actual_energy_kwh"],
                "cumulative_energy_kwh": current_energy,
                "production_units": m_eff["production_units"],
                "sec": m_eff["actual_sec_kwh_per_unit"],
                "deviation_pct": m_savings["baseline_gap_pct"],
                "deviation_status": m_savings.get("deviation_status", "NORMAL"),
                "health_score": health,
            })
        else:
            machine_status_list.append({
                "machine_id": m_id,
                "name": name,
                "state": "OFF",
                "power_kw": 0.0,
                "energy_kwh": 0.0,
                "production_units": 0,
                "sec": None,
                "deviation_pct": 0.0,
                "deviation_status": "NORMAL",
                "health_score": 100.0,
            })

    total_actual_energy = round(total_actual_energy, 4)
    total_expected_energy = round(total_expected_energy, 4)
    total_potential_savings_kwh = round(total_potential_savings_kwh, 4)
    total_potential_savings_inr = round(total_potential_savings_inr, 2)
    total_potential_co2_kg = round(total_potential_co2_kg, 4)

    # 2. Factory SEC: Total Energy / Total Units (None if 0 units)
    factory_sec = round(total_actual_energy / total_production_units, 4) if total_production_units > 0 else None

    # 3. Overall Deviation
    dev_kwh = round(total_actual_energy - total_expected_energy, 4)
    dev_pct = round((dev_kwh / total_expected_energy * 100.0), 2) if total_expected_energy > 0 else 0.0
    dev_status = "HIGH" if dev_pct >= settings.DEVIATION_THRESHOLD_HIGH else ("ELEVATED" if dev_pct >= settings.DEVIATION_THRESHOLD_ELEVATED else "NORMAL")
    if dev_kwh <= 0:
        total_potential_savings_kwh = 0.0
        total_potential_savings_inr = 0.0
        total_potential_co2_kg = 0.0
    else:
        total_potential_savings_kwh = dev_kwh
        total_potential_savings_inr = round(dev_kwh * settings.ELECTRICITY_TARIFF_INR_PER_KWH, 2)
        total_potential_co2_kg = round(dev_kwh * settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH, 4)

    # 4. Factory Forecast (1-5 minutes)
    try:
        forecast_res = forecasting_service.forecast_factory(horizon_minutes=5)
        step_intervals = [
            {"step": i + 1, "forecast_energy_kwh": val}
            for i, val in enumerate(forecast_res.get("factory_step_forecasts_kwh", []))
        ]
        forecast_data = {
            "horizon_minutes": 5,
            "total_forecast_kwh": forecast_res.get("total_factory_forecast_kwh", 0.0),
            "model_type": forecast_res.get("model", "GradientBoostingRegressor"),
            "intervals": step_intervals,
        }
    except Exception as fe:
        logger.warning("Error fetching factory forecast for demo: %s", fe)
        forecast_data = {
            "horizon_minutes": 5,
            "total_forecast_kwh": round(total_actual_energy * 0.1, 4),
            "model_type": "GradientBoostingRegressor",
            "intervals": [],
        }

    # 5. Optimization Opportunities
    opportunities = opportunity_engine.evaluate_factory(
        machine_records_dict,
        tariff_inr=settings.ELECTRICITY_TARIFF_INR_PER_KWH,
    )

    # 6. Utilization calculation
    # Average active machines over observed
    active_count = sum(1 for m in machine_status_list if m["state"] in ("RUNNING", "DEGRADED", "OVERLOAD"))
    utilization_rate = round(active_count / len(all_machine_ids), 2) if all_machine_ids else 0.0

    snapshot = DemoFactorySnapshotResponse(
        timestamp=latest_ts,
        machines=all_machine_ids,
        production={
            "total_units": total_production_units,
            "active_producing_machines": sum(1 for m in machine_status_list if m["production_units"] > 0),
            "running_machines": sum(1 for m in machine_status_list if m["state"] == "RUNNING"),
        },
        energy={
            "actual_energy_kwh": total_actual_energy,
            "expected_energy_kwh": total_expected_energy,
            "total_power_kw": round(sum(m["power_kw"] for m in machine_status_list), 2),
            "cost_inr": round(total_actual_energy * settings.ELECTRICITY_TARIFF_INR_PER_KWH, 2),
            "co2_kg": round(total_actual_energy * settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH, 4),
            "tariff_inr_per_kwh": settings.ELECTRICITY_TARIFF_INR_PER_KWH,
            "emission_factor_kg_per_kwh": settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH,
        },
        sec=factory_sec,
        utilization=utilization_rate,
        baseline={
            "expected_energy_kwh": total_expected_energy,
            "model_type": "Production-Aware Expected-Energy Baseline v2",
            "methodology": "Retrospective ML baseline conditioned on operating state and production output",
        },
        deviation={
            "deviation_kwh": dev_kwh,
            "deviation_pct": dev_pct,
            "status": dev_status,
        },
        forecast=forecast_data,
        savings={
            "potential_savings_kwh": total_potential_savings_kwh,
            "potential_savings_inr": total_potential_savings_inr,
            "potential_co2_kg": total_potential_co2_kg,
            "verified_savings_kwh": 0.0,
            "verification_status": "INSUFFICIENT_DATA" if total_production_units == 0 else "NO_IMPROVEMENT",
            "note": "Potential savings derived from gross above-baseline operation; not guaranteed.",
        },
        efficiency={
            "sec_kwh_per_unit": factory_sec,
            "status": "NORMAL" if dev_status == "NORMAL" else "OPPORTUNITY_IDENTIFIED",
        },
        optimization_opportunities=opportunities,
        machine_status=machine_status_list,
        analysis_window=demo_state.get_active_demo_window(),
    )
    demo_state.set_active_demo_snapshot(snapshot.model_dump())
    return snapshot


@router.get("/machine/{machine_id}", response_model=DemoMachineDetailResponse)
def get_demo_machine(machine_id: str):
    """
    Returns unified intelligence for a specific machine:
    - Current operating state, power, energy, and production
    - SEC (Specific Energy Consumption) and utilization
    - Expected baseline vs actual deviation
    - 1-5 minute future energy forecast
    - Potential savings opportunity
    - Person 2 machine-health context
    - Actionable optimization opportunities
    """
    clean_id = machine_id.strip().upper()
    if clean_id not in DEFAULT_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id}' is not configured in this factory.",
        )

    profile = DEFAULT_PROFILES.get(clean_id)
    machine_name = profile.name if profile else f"Machine {clean_id}"
    machine_type = profile.name.split()[0] if profile else "Industrial Asset"

    recs = _load_demo_telemetry(machine_id=clean_id, limit=60)
    if not recs:
        return DemoMachineDetailResponse(
            machine_id=clean_id,
            machine_name=machine_name,
            machine_type=machine_type,
            current_state="OFF",
            power_kw=0.0,
            energy_kwh=0.0,
            production_units=0,
            sec=None,
            utilization_rate=0.0,
            baseline_expected_energy_kwh=None,
            deviation_kwh=None,
            deviation_pct=None,
            deviation_status="NORMAL",
            forecast_next_5min_kwh=None,
            savings_opportunity={},
            efficiency={},
            health_context={"status": "NO_TELEMETRY"},
            optimization_opportunities=[],
        )

    latest = recs[-1]
    current_state = latest.machine_state.value if hasattr(latest.machine_state, "value") else str(latest.machine_state)
    power_kw = round(latest.power_kw, 2)
    energy_kwh = round(latest.energy_kwh, 4)
    prod_units = int(latest.production_count or 0)

    # Analytics & Savings
    savings = compute_machine_savings(recs, tariff_inr=settings.ELECTRICITY_TARIFF_INR_PER_KWH)
    eff = compute_machine_efficiency(recs)
    opportunities = opportunity_engine.evaluate_machine(clean_id, recs, tariff_inr=settings.ELECTRICITY_TARIFF_INR_PER_KWH)

    # Forecast
    try:
        m_fc = forecasting_service.forecast_machine(clean_id, horizon_minutes=5)
        forecast_next_5min = m_fc["total_forecast_kwh"]
    except Exception:
        forecast_next_5min = round(power_kw * (5.0 / 60.0), 4)

    # Utilization
    productive_samples = sum(1 for r in recs if r.machine_state in (MachineState.RUNNING, MachineState.DEGRADED, MachineState.OVERLOAD))
    utilization_rate = round(productive_samples / len(recs), 2) if recs else 0.0

    return DemoMachineDetailResponse(
        machine_id=clean_id,
        machine_name=machine_name,
        machine_type=machine_type,
        current_state=current_state,
        power_kw=power_kw,
        energy_kwh=energy_kwh,
        actual_energy_kwh=savings["actual_energy_kwh"],
        production_units=eff["production_units"],
        sec=eff["actual_sec_kwh_per_unit"],
        utilization_rate=utilization_rate,
        baseline_expected_energy_kwh=savings["expected_energy_kwh"],
        deviation_kwh=savings["deviation_kwh"],
        deviation_pct=savings["baseline_gap_pct"],
        deviation_status=savings.get("deviation_status", "NORMAL"),
        forecast_next_5min_kwh=forecast_next_5min,
        savings_opportunity={
            "actual_energy_kwh": savings["actual_energy_kwh"],
            "expected_energy_kwh": savings["expected_energy_kwh"],
            "potential_savings_kwh": savings["potential_savings_kwh"],
            "potential_savings_inr": savings["potential_savings_inr"],
            "potential_co2_kg": savings.get("potential_co2_savings_kg", savings.get("potential_co2_kg", 0.0)),
            "persistent_opportunity_kwh": savings.get("persistent_opportunity_kwh", 0.0),
        },
        efficiency={
            "actual_sec": eff["actual_sec_kwh_per_unit"],
            "expected_sec": eff.get("expected_sec_kwh_per_unit"),
            "sec_improvement_pct": eff.get("sec_improvement_pct"),
        },
        health_context={
            "health_score": round(latest.health_score if latest.health_score is not None else 100.0, 1),
            "anomaly_score": round(latest.anomaly_score if latest.anomaly_score is not None else 0.0, 3),
            "temperature_c": round(latest.temperature_c if latest.temperature_c is not None else 45.0, 1),
            "vibration": round(latest.vibration if latest.vibration is not None else 0.15, 3),
            "rpm": round(latest.rpm if latest.rpm is not None else (1450.0 if str(latest.machine_state.value if hasattr(latest.machine_state, 'value') else latest.machine_state) == "RUNNING" else 0.0), 1),
            "source": "Person 2 Machine-Health Layer",
        },
        optimization_opportunities=opportunities,
    )


@router.post("/reset")
def reset_demo():
    """Resets demonstration state buffer and establishes a clean baseline."""
    demo_state.reset()
    return {"status": "RESET", "message": "Demo state successfully reset to initial idle state."}


@router.post("/run")
def trigger_demo_run(steps_per_phase: int = Query(default=10, ge=1, le=30)):
    """Triggers end-to-end 6-phase factory demonstration run and updates authoritative state."""
    from scripts.run_factory_demo import run_pipeline_demo
    result = run_pipeline_demo(steps_per_phase=steps_per_phase, dt_seconds=1.0)
    return {
        "status": "COMPLETED",
        "steps_per_phase": steps_per_phase,
        "summary": result,
    }

