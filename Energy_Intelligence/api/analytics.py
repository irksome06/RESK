"""
Deterministic Energy & Production Analytics API Endpoints.
Provides machine-level and factory-level KPIs over explicit time windows:
- Specific Energy Consumption (SEC) & Energy per unit
- Production throughput and rates
- Operational machine utilization
- Granular operational state energy allocations (running, idle, sleep, degraded, overload)
- Electricity costs (INR) and CO2 emissions
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.schemas import MachineEnergyAnalysis, FactoryEnergyAnalysis
from database.telemetry_repository import telemetry_repo
from simulator.machine_simulator import DEFAULT_PROFILES
from analytics.engine import analyze_machine, analyze_factory

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/machines/{machine_id}", response_model=MachineEnergyAnalysis)
def get_machine_analytics(
    machine_id: str,
    start_time: datetime = Query(..., description="Start timestamp of observation window (ISO 8601 UTC)"),
    end_time: datetime = Query(..., description="End timestamp of observation window (ISO 8601 UTC)"),
    tariff_inr: Optional[float] = Query(None, description="Optional electricity tariff override in INR/kWh"),
    emission_factor: Optional[float] = Query(None, description="Optional CO2 emission factor override in kg CO2/kWh"),
    db: Session = Depends(get_db),
):
    """
    Computes deterministic energy and production metrics for a specific machine over [start_time, end_time].
    Returns HTTP 404 if machine is neither configured nor observed in database.
    """
    clean_id = machine_id.strip()
    known_db_ids = telemetry_repo.get_known_machine_ids(db=db)
    if clean_id not in DEFAULT_PROFILES and clean_id not in known_db_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{clean_id}' not found",
        )

    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be strictly earlier than end_time",
        )

    return analyze_machine(
        machine_id=clean_id,
        start_time=start_time,
        end_time=end_time,
        electricity_rate_inr_per_kwh=tariff_inr,
        grid_emission_factor_kg_per_kwh=emission_factor,
        db=db,
    )


@router.get("/factory", response_model=FactoryEnergyAnalysis)
def get_factory_analytics(
    start_time: datetime = Query(..., description="Start timestamp of observation window (ISO 8601 UTC)"),
    end_time: datetime = Query(..., description="End timestamp of observation window (ISO 8601 UTC)"),
    tariff_inr: Optional[float] = Query(None, description="Optional electricity tariff override in INR/kWh"),
    emission_factor: Optional[float] = Query(None, description="Optional CO2 emission factor override in kg CO2/kWh"),
    db: Session = Depends(get_db),
):
    """
    Computes factory-wide deterministic energy and production metrics aggregating all observed machines.
    Calculates factory SEC = Total Energy / Total Production (mathematically correct aggregation).
    """
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be strictly earlier than end_time",
        )

    return analyze_factory(
        start_time=start_time,
        end_time=end_time,
        electricity_rate_inr_per_kwh=tariff_inr,
        grid_emission_factor_kg_per_kwh=emission_factor,
        db=db,
    )
