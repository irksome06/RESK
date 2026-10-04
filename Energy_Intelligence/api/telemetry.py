"""
Telemetry API Endpoints.
Provides REST validation, database persistence, and query interfaces for canonical industrial machine telemetry.
Backed by PostgreSQL / relational persistence with idempotent duplicate protection.
"""

from typing import List, Optional
from fastapi import APIRouter, status, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.schemas import TelemetryRecord, TelemetryAcceptedResponse
from database.telemetry_repository import telemetry_repo

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("/status")
def telemetry_status(db: Session = Depends(get_db)):
    """Health check for the telemetry ingestion pipeline."""
    return {
        "status": "Telemetry API operational",
        "ingested_records_count": telemetry_repo.count_telemetry(db=db),
    }


@router.post("", response_model=TelemetryAcceptedResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TelemetryAcceptedResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def ingest_telemetry(record: TelemetryRecord, db: Session = Depends(get_db)):
    """
    Ingest and validate a single canonical telemetry record.
    Persists record to PostgreSQL / relational storage.
    If a record with identical (machine_id, timestamp) already exists, returns HTTP 409 Conflict.
    """
    _, is_new = telemetry_repo.save_telemetry(record, db=db)
    if not is_new:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate telemetry record for machine '{record.machine_id}' at timestamp '{record.timestamp.isoformat()}' already exists",
        )

    return TelemetryAcceptedResponse(
        status="accepted",
        machine_id=record.machine_id,
        timestamp=record.timestamp,
        message="Telemetry persisted",
    )


@router.get("", response_model=List[TelemetryRecord])
@router.get("/", response_model=List[TelemetryRecord], include_in_schema=False)
def list_telemetry(
    machine_id: Optional[str] = Query(None, description="Optional filter by machine ID (e.g. M01)"),
    limit: int = Query(50, ge=1, le=1000, description="Max number of recent records (newest first)"),
    db: Session = Depends(get_db),
):
    """
    Query recent telemetry records in reverse chronological order from persistent storage.
    Optionally filter by machine_id.
    """
    return telemetry_repo.get_recent_telemetry(limit=limit, machine_id=machine_id, db=db)


@router.get("/latest/{machine_id}", response_model=TelemetryRecord)
def get_latest_telemetry(machine_id: str, db: Session = Depends(get_db)):
    """
    Fetch the single most recent telemetry record for a specified machine from persistent storage.
    Returns HTTP 404 if no telemetry has been recorded for the asset.
    """
    record = telemetry_repo.get_latest_telemetry(machine_id, db=db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id}' telemetry not found",
        )
    return record
