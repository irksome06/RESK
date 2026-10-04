"""
Factory & Machine Metrics Endpoints.
Provides instantaneous factory snapshots derived directly from current persistent telemetry in PostgreSQL.
Analytics and ML baselines are added in subsequent phases.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.schemas import FactorySnapshot
from database.telemetry_repository import telemetry_repo

router = APIRouter(tags=["Metrics"])


@router.get("/factory/snapshot", response_model=FactorySnapshot)
def get_factory_snapshot(db: Session = Depends(get_db)):
    """
    Lightweight factory state snapshot aggregating current operational states,
    total active power demand, and cumulative production from latest machine telemetry
    queried from the persistent database.
    (Note: Full SEC, baseline modeling, and ML predictions are implemented in later phases).
    """
    return telemetry_repo.get_factory_snapshot(db=db)


@router.get("/factory/kpis")
def get_factory_kpis(db: Session = Depends(get_db)):
    """
    Factory-wide KPI endpoint (placeholder preserved from Phase 1).
    Full deterministic and ML analytics implemented in Phase 7 & 15.
    """
    snapshot = telemetry_repo.get_factory_snapshot(db=db)
    return {
        "status": "operational",
        "machines_seen": snapshot.machines_seen,
        "total_power_kw": snapshot.total_power_kw,
        "total_production_units": snapshot.total_production or 0,
        "average_sec": None,  # Computed in Phase 7
    }
