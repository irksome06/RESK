"""
Unit & Integration Test Suite for Phase 6: PostgreSQL Database Persistence.
Validates SQLAlchemy 2.x engine, session lifecycle, TelemetryDB schema, indexes,
idempotent duplicate protection, timezone handling, repository operations,
and FastAPI DB integration with zero dependencies on external live services.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

from database.database import (
    Base,
    engine,
    SessionLocal,
    init_db,
    get_db,
    get_db_context,
    check_db_connected,
)
from database.models import TelemetryDB, Machine
from database.telemetry_repository import TelemetryRepository, telemetry_repo
from database.schemas import TelemetryRecord, MachineState, TelemetrySource
from simulator.config import settings
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a clean database state before and after each test."""
    telemetry_repo.clear_all()
    yield
    telemetry_repo.clear_all()


# ==============================================================================
# 1. DATABASE ENGINE & SESSION TESTS
# ==============================================================================

def test_database_engine_and_session_creation():
    """Verify engine connectivity, session factory, and basic transaction execution."""
    assert engine is not None
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1

    session = SessionLocal()
    try:
        val = session.execute(text("SELECT 100")).scalar()
        assert val == 100
    finally:
        session.close()


def test_table_and_model_creation():
    """Verify ORM models and tables are registered in Base metadata with expected constraints."""
    init_db()
    table_names = list(Base.metadata.tables.keys())
    assert "telemetry" in table_names
    assert "machines" in table_names

    telemetry_table = Base.metadata.tables["telemetry"]
    col_names = [c.name for c in telemetry_table.columns]
    expected_cols = [
        "id", "timestamp", "machine_id", "power_kw", "energy_kwh", "machine_state",
        "production_count", "production_delta", "cycle_time_sec", "voltage_v",
        "current_a", "temperature_c", "vibration", "rpm", "torque_nm",
        "health_score", "anomaly_score", "source", "schema_version", "created_at",
    ]
    for col in expected_cols:
        assert col in col_names, f"Missing column {col} in telemetry table"

    # Check unique constraint
    unique_constraints = [c.name for c in telemetry_table.constraints if hasattr(c, "name")]
    assert "uq_telemetry_machine_timestamp" in unique_constraints


# ==============================================================================
# 2. PERSISTENCE, RETRIEVAL & FILTERING
# ==============================================================================

def test_valid_telemetry_insertion():
    """Verify inserting valid telemetry returns is_new=True and updates count."""
    record = TelemetryRecord(
        timestamp=datetime(2026, 10, 2, 14, 0, 0, tzinfo=timezone.utc),
        machine_id="M01",
        power_kw=7.5,
        energy_kwh=120.0,
        machine_state=MachineState.RUNNING,
        production_count=100,
        production_delta=2,
    )
    saved, is_new = telemetry_repo.save_telemetry(record)
    assert is_new is True
    assert saved.machine_id == "M01"
    assert saved.power_kw == 7.5
    assert telemetry_repo.count_telemetry() == 1


def test_telemetry_retrieval_and_ordering():
    """Verify records are returned in reverse chronological order (newest first)."""
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(3):
        telemetry_repo.save_telemetry(
            TelemetryRecord(
                timestamp=t0 + timedelta(minutes=i),
                machine_id="M01",
                power_kw=float(i + 1),
                energy_kwh=10.0,
                machine_state=MachineState.RUNNING,
            )
        )

    records = telemetry_repo.get_recent_telemetry(limit=10)
    assert len(records) == 3
    # Newest (i=2) must be first
    assert records[0].power_kw == 3.0
    assert records[1].power_kw == 2.0
    assert records[2].power_kw == 1.0


def test_latest_telemetry_retrieval():
    """Verify get_latest_telemetry retrieves the single newest observation for a machine."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    telemetry_repo.save_telemetry(
        TelemetryRecord(
            timestamp=t0,
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.IDLE,
        )
    )
    telemetry_repo.save_telemetry(
        TelemetryRecord(
            timestamp=t0 + timedelta(seconds=10),
            machine_id="M01",
            power_kw=8.2,
            energy_kwh=10.02,
            machine_state=MachineState.RUNNING,
        )
    )
    telemetry_repo.save_telemetry(
        TelemetryRecord(
            timestamp=t0 + timedelta(seconds=20),
            machine_id="M02",
            power_kw=3.5,
            energy_kwh=5.0,
            machine_state=MachineState.RUNNING,
        )
    )

    latest_m1 = telemetry_repo.get_latest_telemetry("M01")
    assert latest_m1 is not None
    assert latest_m1.machine_id == "M01"
    assert latest_m1.power_kw == 8.2
    assert latest_m1.machine_state == MachineState.RUNNING

    latest_m2 = telemetry_repo.get_latest_telemetry("M02")
    assert latest_m2 is not None
    assert latest_m2.machine_id == "M02"
    assert latest_m2.power_kw == 3.5

    assert telemetry_repo.get_latest_telemetry("M99") is None


def test_machine_filtering_and_counts():
    """Verify filtering by machine_id isolates observations and reports per-machine counts."""
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=7.0, energy_kwh=1.0, machine_state=MachineState.RUNNING)
    )
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0, machine_id="M02", power_kw=6.0, energy_kwh=2.0, machine_state=MachineState.RUNNING)
    )
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0 + timedelta(seconds=1), machine_id="M02", power_kw=6.5, energy_kwh=2.1, machine_state=MachineState.RUNNING)
    )

    m2_records = telemetry_repo.get_recent_telemetry(machine_id="M02")
    assert len(m2_records) == 2
    assert all(r.machine_id == "M02" for r in m2_records)

    assert telemetry_repo.get_machine_telemetry_count("M01") == 1
    assert telemetry_repo.get_machine_telemetry_count("M02") == 2
    assert telemetry_repo.get_machine_telemetry_count("M03") == 0

    known = telemetry_repo.get_known_machine_ids()
    assert known == ["M01", "M02"]


def test_limit_handling():
    """Verify limit parameter properly bounds query result sets."""
    t0 = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(15):
        telemetry_repo.save_telemetry(
            TelemetryRecord(
                timestamp=t0 + timedelta(seconds=i),
                machine_id="M01",
                power_kw=float(i),
                energy_kwh=float(i),
                machine_state=MachineState.RUNNING,
            )
        )

    assert len(telemetry_repo.get_recent_telemetry(limit=5)) == 5
    assert len(telemetry_repo.get_recent_telemetry(limit=10)) == 10
    assert len(telemetry_repo.get_recent_telemetry(limit=50)) == 15


# ==============================================================================
# 3. IDEMPOTENCY & DUPLICATE PROTECTION (MQTT QoS 1)
# ==============================================================================

def test_duplicate_telemetry_protection():
    """
    Verify duplicate telemetry (same machine_id and timestamp) does not create
    a second database row and returns is_new=False without error.
    """
    ts = datetime(2026, 10, 2, 15, 30, 0, tzinfo=timezone.utc)
    record = TelemetryRecord(
        timestamp=ts,
        machine_id="M01",
        power_kw=7.8,
        energy_kwh=100.0,
        machine_state=MachineState.RUNNING,
    )

    # First insertion
    saved1, is_new1 = telemetry_repo.save_telemetry(record)
    assert is_new1 is True
    assert telemetry_repo.count_telemetry() == 1

    # Duplicate insertion (simulating MQTT QoS 1 retry)
    saved2, is_new2 = telemetry_repo.save_telemetry(record)
    assert is_new2 is False
    assert telemetry_repo.count_telemetry() == 1
    assert saved2.machine_id == "M01"
    assert saved2.power_kw == 7.8


def test_save_telemetry_batch_with_duplicates():
    """Verify batch insertion persists unique records and skips duplicate items cleanly."""
    ts1 = datetime(2026, 10, 2, 16, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 10, 2, 16, 1, 0, tzinfo=timezone.utc)

    records = [
        TelemetryRecord(timestamp=ts1, machine_id="M01", power_kw=5.0, energy_kwh=1.0, machine_state=MachineState.RUNNING),
        TelemetryRecord(timestamp=ts1, machine_id="M01", power_kw=5.0, energy_kwh=1.0, machine_state=MachineState.RUNNING),  # duplicate
        TelemetryRecord(timestamp=ts2, machine_id="M01", power_kw=5.2, energy_kwh=1.1, machine_state=MachineState.RUNNING),
    ]

    inserted = telemetry_repo.save_telemetry_batch(records)
    assert inserted == 2
    assert telemetry_repo.count_telemetry() == 2


# ==============================================================================
# 4. FIELD TYPES, NULLABILITY & TIMEZONES
# ==============================================================================

def test_nullable_optional_fields():
    """Verify optional fields (sensor diagnostics, production metrics) remain None when missing."""
    record = TelemetryRecord(
        timestamp=datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc),
        machine_id="M04",
        power_kw=2.5,
        energy_kwh=50.0,
        machine_state=MachineState.IDLE,
        production_count=None,
        production_delta=None,
        voltage_v=None,
        vibration=None,
        health_score=None,
    )
    saved, is_new = telemetry_repo.save_telemetry(record)
    assert is_new is True
    assert saved.production_count is None
    assert saved.voltage_v is None
    assert saved.vibration is None
    assert saved.health_score is None


def test_machine_state_persistence():
    """Verify all MachineState enum values serialize to and from persistent storage correctly."""
    states = [
        MachineState.IDLE,
        MachineState.RUNNING,
        MachineState.SLEEP,
        MachineState.DEGRADED,
        MachineState.OVERLOAD,
    ]
    t0 = datetime(2026, 10, 2, 14, 0, 0, tzinfo=timezone.utc)

    for i, st in enumerate(states):
        telemetry_repo.save_telemetry(
            TelemetryRecord(
                timestamp=t0 + timedelta(seconds=i),
                machine_id=f"M0{i+1}",
                power_kw=float(i + 1),
                energy_kwh=10.0,
                machine_state=st,
            )
        )

    for i, st in enumerate(states):
        rec = telemetry_repo.get_latest_telemetry(f"M0{i+1}")
        assert rec is not None
        assert rec.machine_state == st


def test_timestamp_timezone_behavior():
    """Verify timestamps retain UTC timezone information across save and retrieval."""
    utc_ts = datetime(2026, 10, 2, 18, 30, 45, tzinfo=timezone.utc)
    record = TelemetryRecord(
        timestamp=utc_ts,
        machine_id="M01",
        power_kw=7.2,
        energy_kwh=300.0,
        machine_state=MachineState.RUNNING,
    )
    saved, _ = telemetry_repo.save_telemetry(record)
    assert saved.timestamp.tzinfo is not None
    assert saved.timestamp == utc_ts


def test_database_rollback_after_failed_transaction():
    """Verify session rollback cleans up state and allows subsequent transactions to succeed."""
    with get_db_context() as session:
        try:
            # Force an integrity error by inserting invalid raw model
            session.add(TelemetryDB(machine_id="M01"))  # missing required non-null fields
            session.flush()
        except Exception:
            session.rollback()

    # Verify session factory is healthy for next transaction
    ts = datetime(2026, 10, 2, 20, 0, 0, tzinfo=timezone.utc)
    valid_rec = TelemetryRecord(
        timestamp=ts,
        machine_id="M01",
        power_kw=6.0,
        energy_kwh=10.0,
        machine_state=MachineState.RUNNING,
    )
    saved, is_new = telemetry_repo.save_telemetry(valid_rec)
    assert is_new is True
    assert telemetry_repo.count_telemetry() == 1


# ==============================================================================
# 5. FASTAPI REST INTEGRATION WITH PERSISTENT DB
# ==============================================================================

def test_fastapi_post_persists_to_db():
    """Verify POST /telemetry validates, persists to database, and returns 201 Created."""
    payload = {
        "timestamp": "2026-10-02T12:00:00Z",
        "machine_id": "M01",
        "power_kw": 7.8,
        "energy_kwh": 150.0,
        "machine_state": "RUNNING",
        "production_count": 50,
        "production_delta": 1,
    }
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["machine_id"] == "M01"
    assert telemetry_repo.count_telemetry() == 1

    stored = telemetry_repo.get_latest_telemetry("M01")
    assert stored is not None
    assert stored.power_kw == 7.8


def test_fastapi_post_duplicate_returns_409():
    """Verify duplicate POST /telemetry returns HTTP 409 Conflict and creates no duplicate rows."""
    payload = {
        "timestamp": "2026-10-02T12:00:00Z",
        "machine_id": "M01",
        "power_kw": 7.8,
        "energy_kwh": 150.0,
        "machine_state": "RUNNING",
    }
    # First request
    res1 = client.post("/telemetry", json=payload)
    assert res1.status_code == 201

    # Second request with identical (machine_id, timestamp)
    res2 = client.post("/telemetry", json=payload)
    assert res2.status_code == 409
    assert "Duplicate telemetry record" in res2.json()["detail"]
    assert telemetry_repo.count_telemetry() == 1


def test_fastapi_get_telemetry_reads_from_db():
    """Verify GET /telemetry queries the persistent database and supports machine filtering."""
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=5.0, energy_kwh=10.0, machine_state=MachineState.RUNNING)
    )
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0 + timedelta(seconds=1), machine_id="M02", power_kw=8.0, energy_kwh=20.0, machine_state=MachineState.RUNNING)
    )

    res = client.get("/telemetry?machine_id=M02")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["machine_id"] == "M02"
    assert items[0]["power_kw"] == 8.0


def test_fastapi_get_latest_from_db():
    """Verify GET /telemetry/latest/{machine_id} retrieves latest observation from DB."""
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=5.0, energy_kwh=10.0, machine_state=MachineState.RUNNING)
    )
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0 + timedelta(minutes=1), machine_id="M01", power_kw=9.2, energy_kwh=10.5, machine_state=MachineState.RUNNING)
    )

    res = client.get("/telemetry/latest/M01")
    assert res.status_code == 200
    assert res.json()["power_kw"] == 9.2

    # Unknown machine
    res_404 = client.get("/telemetry/latest/UNKNOWN_99")
    assert res_404.status_code == 404


def test_fastapi_factory_snapshot_derives_from_db():
    """Verify GET /factory/snapshot aggregates latest observations from persistent database."""
    t0 = datetime(2026, 10, 2, 11, 0, 0, tzinfo=timezone.utc)
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=7.5, energy_kwh=50.0, machine_state=MachineState.RUNNING, production_count=100)
    )
    telemetry_repo.save_telemetry(
        TelemetryRecord(timestamp=t0 + timedelta(seconds=5), machine_id="M02", power_kw=1.2, energy_kwh=20.0, machine_state=MachineState.IDLE, production_count=40)
    )

    res = client.get("/factory/snapshot")
    assert res.status_code == 200
    data = res.json()
    assert data["machines_seen"] == 2
    assert data["machines_running"] == 1
    assert data["machines_idle"] == 1
    assert round(data["total_power_kw"], 1) == 8.7
    assert data["total_production"] == 140


def test_empty_database_behavior():
    """Verify clean empty-state handling across repository and snapshot endpoints."""
    assert telemetry_repo.count_telemetry() == 0
    assert telemetry_repo.get_recent_telemetry() == []
    assert telemetry_repo.get_latest_telemetry("M01") is None
    assert telemetry_repo.get_known_machine_ids() == []

    snapshot = telemetry_repo.get_factory_snapshot()
    assert snapshot.machines_seen == 0
    assert snapshot.total_power_kw == 0.0

    res = client.get("/factory/snapshot")
    assert res.status_code == 200
    assert res.json()["machines_seen"] == 0
