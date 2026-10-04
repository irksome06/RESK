"""
Machine Asset API Endpoints.
Provides machine inventory and live operational summaries combining static engineering specs
with dynamic observations queried directly from persistent database storage.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.schemas import MachineSummary
from simulator.machine_simulator import DEFAULT_PROFILES
from database.telemetry_repository import telemetry_repo

router = APIRouter(prefix="/machines", tags=["Machines"])


def _build_machine_summary(machine_id: str, db: Optional[Session] = None) -> MachineSummary:
    """Combines static machine profile with observed dynamic telemetry from database."""
    profile = DEFAULT_PROFILES.get(machine_id)
    latest_rec = telemetry_repo.get_latest_telemetry(machine_id, db=db)
    total_count = telemetry_repo.get_machine_telemetry_count(machine_id, db=db)

    name = profile.name if profile else f"Industrial Asset {machine_id}"
    rated_kw = profile.rated_power_kw if profile else 7.5
    nominal_uph = profile.nominal_uph if profile else None

    return MachineSummary(
        machine_id=machine_id,
        name=name,
        rated_power_kw=rated_kw,
        nominal_uph=nominal_uph,
        last_seen=latest_rec.timestamp if latest_rec else None,
        machine_state=latest_rec.machine_state if latest_rec else None,
        current_power_kw=latest_rec.power_kw if latest_rec else None,
        current_energy_kwh=latest_rec.energy_kwh if latest_rec else None,
        total_telemetry_count=total_count,
    )


@router.get("", response_model=List[MachineSummary])
@router.get("/", response_model=List[MachineSummary], include_in_schema=False)
def list_machines(db: Session = Depends(get_db)):
    """
    List all known machines. Combines configured factory profiles (M01-M04)
    with any dynamically discovered machines from persistent telemetry history.
    """
    known_db_ids = telemetry_repo.get_known_machine_ids(db=db)
    all_machine_ids = sorted(list(set(DEFAULT_PROFILES.keys()) | set(known_db_ids)))
    return [_build_machine_summary(m_id, db=db) for m_id in all_machine_ids]


@router.get("/{machine_id}", response_model=MachineSummary)
def get_machine(machine_id: str, db: Session = Depends(get_db)):
    """
    Fetch comprehensive asset summary and latest operational state for a specific machine.
    Returns HTTP 404 if machine is neither configured nor observed in database.
    """
    clean_id = machine_id.strip()
    known_db_ids = telemetry_repo.get_known_machine_ids(db=db)
    if clean_id not in DEFAULT_PROFILES and clean_id not in known_db_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{clean_id}' not found",
        )
    return _build_machine_summary(clean_id, db=db)
