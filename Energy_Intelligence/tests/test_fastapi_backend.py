"""
Phase 5 FastAPI Backend Integration & Unit Test Suite.
Validates REST endpoints, in-memory telemetry buffer, query filtering, machine inventory,
factory snapshot derivation, bounded store eviction, and offline MQTT resilience.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

# Ensure person3_energy_intelligence is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from api.main import app
from api.telemetry_store import telemetry_store, InMemoryTelemetryStore, ingest_telemetry_record
from database.schemas import TelemetryRecord, MachineState


@pytest.fixture(autouse=True)
def clean_telemetry_store():
    """Ensure in-memory telemetry store is clean before each test."""
    telemetry_store.clear()
    yield
    telemetry_store.clear()


client = TestClient(app)


# ==============================================================================
# 1. BASE API & HEALTH ENDPOINTS
# ==============================================================================

def test_root_endpoint():
    """Verify GET / returns service metadata and status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "online")
    assert data["service"] == "person3-energy-intelligence"
    assert data["version"] == "1.0.0"


def test_health_endpoint():
    """Verify GET /health returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# ==============================================================================
# 2. TELEMETRY INGESTION (POST /telemetry)
# ==============================================================================

def test_post_valid_telemetry():
    """Verify POST /telemetry accepts valid payload and adds it to the store."""
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

    # Confirm ingested into store
    assert telemetry_store.count() == 1
    recent = telemetry_store.get_recent(limit=10)
    assert len(recent) == 1
    assert recent[0].machine_id == "M01"
    assert recent[0].power_kw == 7.8


def test_post_invalid_telemetry_rejected():
    """Verify POST /telemetry rejects invalid payloads with HTTP 422."""
    # Negative power
    bad_payload = {
        "timestamp": "2026-10-02T12:00:00Z",
        "machine_id": "M01",
        "power_kw": -10.0,
        "energy_kwh": 150.0,
        "machine_state": "RUNNING",
    }
    response = client.post("/telemetry", json=bad_payload)
    assert response.status_code == 422
    assert telemetry_store.count() == 0


# ==============================================================================
# 3. TELEMETRY QUERYING & FILTERING (GET /telemetry)
# ==============================================================================

def test_get_telemetry_ordering_and_filtering():
    """Verify GET /telemetry returns reverse chronological order and filters by machine_id."""
    # Ingest records with incrementing power
    t1 = TelemetryRecord(
        timestamp=datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc),
        machine_id="M01",
        power_kw=7.1,
        energy_kwh=10.0,
        machine_state=MachineState.RUNNING,
    )
    t2 = TelemetryRecord(
        timestamp=datetime(2026, 10, 2, 10, 0, 1, tzinfo=timezone.utc),
        machine_id="M02",
        power_kw=6.5,
        energy_kwh=20.0,
        machine_state=MachineState.RUNNING,
    )
    t3 = TelemetryRecord(
        timestamp=datetime(2026, 10, 2, 10, 0, 2, tzinfo=timezone.utc),
        machine_id="M01",
        power_kw=7.9,
        energy_kwh=10.1,
        machine_state=MachineState.RUNNING,
    )
    telemetry_store.add(t1)
    telemetry_store.add(t2)
    telemetry_store.add(t3)

    # All records (newest first)
    resp_all = client.get("/telemetry")
    assert resp_all.status_code == 200
    all_data = resp_all.json()
    assert len(all_data) == 3
    assert all_data[0]["power_kw"] == 7.9  # t3 was added last
    assert all_data[1]["power_kw"] == 6.5  # t2
    assert all_data[2]["power_kw"] == 7.1  # t1

    # Filtered by M01
    resp_m01 = client.get("/telemetry?machine_id=M01")
    assert resp_m01.status_code == 200
    m01_data = resp_m01.json()
    assert len(m01_data) == 2
    assert all(r["machine_id"] == "M01" for r in m01_data)


def test_get_telemetry_limit_validation():
    """Verify limit query parameter respects bounds and rejects negative/zero values."""
    for i in range(15):
        telemetry_store.add(
            TelemetryRecord(
                timestamp=datetime(2026, 10, 2, 10, 0, i, tzinfo=timezone.utc),
                machine_id="M01",
                power_kw=7.0,
                energy_kwh=float(i),
                machine_state=MachineState.RUNNING,
            )
        )

    # Valid limit
    resp = client.get("/telemetry?limit=5")
    assert resp.status_code == 200
    assert len(resp.json()) == 5

    # Invalid limits: 0 and negative must return 422
    assert client.get("/telemetry?limit=0").status_code == 422
    assert client.get("/telemetry?limit=-5").status_code == 422


# ==============================================================================
# 4. LATEST TELEMETRY (GET /telemetry/latest/{machine_id})
# ==============================================================================

def test_get_latest_telemetry_endpoint():
    """Verify GET /telemetry/latest/{machine_id} returns newest record or 404."""
    # Unknown machine -> 404
    resp_unknown = client.get("/telemetry/latest/M99")
    assert resp_unknown.status_code == 404
    assert "not found" in resp_unknown.json()["detail"].lower()

    # Add records for M01
    telemetry_store.add(
        TelemetryRecord(
            timestamp=datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc),
            machine_id="M01",
            power_kw=7.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
        )
    )
    telemetry_store.add(
        TelemetryRecord(
            timestamp=datetime(2026, 10, 2, 10, 0, 5, tzinfo=timezone.utc),
            machine_id="M01",
            power_kw=8.4,
            energy_kwh=10.2,
            machine_state=MachineState.RUNNING,
        )
    )

    resp_latest = client.get("/telemetry/latest/M01")
    assert resp_latest.status_code == 200
    data = resp_latest.json()
    assert data["machine_id"] == "M01"
    assert data["power_kw"] == 8.4


# ==============================================================================
# 5. MACHINE ASSET API (GET /machines & GET /machines/{machine_id})
# ==============================================================================

def test_list_machines_and_detail():
    """Verify machine list combines configured profiles with live telemetry."""
    # Initially no telemetry, but M01-M04 exist in static profiles
    resp = client.get("/machines")
    assert resp.status_code == 200
    machines = resp.json()
    m_ids = {m["machine_id"] for m in machines}
    assert {"M01", "M02", "M03", "M04"}.issubset(m_ids)

    # Ingest telemetry for M01
    telemetry_store.add(
        TelemetryRecord(
            timestamp=datetime(2026, 10, 2, 10, 30, 0, tzinfo=timezone.utc),
            machine_id="M01",
            power_kw=7.65,
            energy_kwh=115.0,
            machine_state=MachineState.RUNNING,
        )
    )

    # Detail check for M01
    resp_m01 = client.get("/machines/M01")
    assert resp_m01.status_code == 200
    m01 = resp_m01.json()
    assert m01["machine_id"] == "M01"
    assert m01["name"] == "CNC Milling Center 1"
    assert m01["rated_power_kw"] == 7.5
    assert m01["machine_state"] == "RUNNING"
    assert m01["current_power_kw"] == 7.65
    assert m01["total_telemetry_count"] == 1

    # Detail check for unknown machine -> 404
    assert client.get("/machines/UNKNOWN_ASSET").status_code == 404


# ==============================================================================
# 6. FACTORY SNAPSHOT (GET /factory/snapshot)
# ==============================================================================

def test_factory_snapshot_calculation():
    """Verify GET /factory/snapshot calculates aggregate counts and power from latest records."""
    # Empty store behavior
    resp_empty = client.get("/factory/snapshot")
    assert resp_empty.status_code == 200
    snap_empty = resp_empty.json()
    assert snap_empty["machines_seen"] == 0
    assert snap_empty["total_power_kw"] == 0.0

    # Ingest telemetry for 3 machines in different states
    telemetry_store.add(
        TelemetryRecord(
            timestamp=datetime(2026, 10, 2, 11, 0, 0, tzinfo=timezone.utc),
            machine_id="M01",
            power_kw=7.5,
            energy_kwh=100.0,
            machine_state=MachineState.RUNNING,
            production_count=100,
        )
    )
    telemetry_store.add(
        TelemetryRecord(
            timestamp=datetime(2026, 10, 2, 11, 0, 0, tzinfo=timezone.utc),
            machine_id="M02",
            power_kw=1.4,
            energy_kwh=50.0,
            machine_state=MachineState.IDLE,
            production_count=0,
        )
    )
    telemetry_store.add(
        TelemetryRecord(
            timestamp=datetime(2026, 10, 2, 11, 0, 0, tzinfo=timezone.utc),
            machine_id="M03",
            power_kw=0.35,
            energy_kwh=80.0,
            machine_state=MachineState.SLEEP,
            production_count=200,
        )
    )

    resp_snap = client.get("/factory/snapshot")
    assert resp_snap.status_code == 200
    snapshot = resp_snap.json()

    assert snapshot["machines_seen"] == 3
    assert snapshot["machines_running"] == 1
    assert snapshot["machines_idle"] == 1
    assert snapshot["machines_sleep"] == 1
    assert snapshot["machines_degraded"] == 0
    assert snapshot["machines_overload"] == 0
    # 7.5 + 1.4 + 0.35 = 9.25 kW
    assert snapshot["total_power_kw"] == 9.25
    # 100 + 0 + 200 = 300 units
    assert snapshot["total_production"] == 300


# ==============================================================================
# 7. BOUNDED STORE & INGESTION INTEGRATION
# ==============================================================================

def test_telemetry_store_bounded_eviction():
    """Verify that inserting beyond max capacity evicts oldest records cleanly."""
    small_store = InMemoryTelemetryStore(max_records=5)
    for i in range(10):
        small_store.add(
            TelemetryRecord(
                timestamp=datetime(2026, 10, 2, 12, 0, i, tzinfo=timezone.utc),
                machine_id="M01",
                power_kw=float(i),
                energy_kwh=10.0,
                machine_state=MachineState.RUNNING,
            )
        )

    assert small_store.count() == 5
    recent = small_store.get_recent(limit=10)
    assert len(recent) == 5
    # Newest is 9, oldest remaining is 5 (0-4 evicted)
    assert recent[0].power_kw == 9.0
    assert recent[-1].power_kw == 5.0


def test_unified_ingest_function():
    """Verify unified ingest_telemetry_record adds directly to telemetry_store."""
    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M04",
        power_kw=5.2,
        energy_kwh=40.0,
        machine_state=MachineState.RUNNING,
    )
    result = ingest_telemetry_record(record)
    assert result == record
    assert telemetry_store.count() == 1
    assert telemetry_store.get_latest("M04") == record


def test_mqtt_callback_to_telemetry_store_integration():
    """Verify MQTTSubscriber on_telemetry callback forwards records to the store."""
    from mqtt.subscriber import MQTTSubscriber

    subscriber = MQTTSubscriber(on_telemetry=ingest_telemetry_record)

    rec = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M02",
        power_kw=6.8,
        energy_kwh=88.5,
        machine_state=MachineState.RUNNING,
    )

    class MockMsg:
        topic = "factory/M02/telemetry"
        payload = rec.model_dump_json().encode("utf-8")

    subscriber._on_message(None, None, MockMsg())

    # Record must be present in telemetry_store
    assert telemetry_store.count() == 1
    assert telemetry_store.get_latest("M02") is not None
    assert telemetry_store.get_latest("M02").power_kw == 6.8


def test_empty_telemetry_store_get():
    """Verify GET /telemetry on empty store returns empty list without error."""
    resp = client.get("/telemetry")
    assert resp.status_code == 200
    assert resp.json() == []


def test_app_starts_when_mqtt_broker_offline():
    """Verify FastAPI application boots and responds normally even when broker is unreachable."""
    with TestClient(app) as test_client:
        resp = test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
