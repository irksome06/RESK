"""
Phase 2 Telemetry Schema Unit and Integration Test Suite.
Validates the canonical telemetry contract, boundaries, Pydantic validations,
JSON serialization roundtrips, and FastAPI ingestion endpoint behavior.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

# Ensure person3_energy_intelligence is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.schemas import TelemetryRecord, TelemetrySource, TelemetryIngestResponse
from simulator.machine_states import MachineState
from api.main import app

client = TestClient(app)


# ==============================================================================
# 1. POSITIVE VALIDATION TESTS
# ==============================================================================

def test_complete_valid_telemetry_record():
    """Verify that a record with all core and optional fields validates cleanly."""
    now_utc = datetime.now(timezone.utc)
    payload = {
        "timestamp": now_utc.isoformat(),
        "machine_id": "M01",
        "power_kw": 7.8,
        "energy_kwh": 125.6,
        "voltage_v": 415.0,
        "current_a": 12.4,
        "production_count": 120,
        "production_delta": 2,
        "cycle_time_sec": 30.0,
        "machine_state": "RUNNING",
        "temperature_c": 52.4,
        "vibration": 0.18,
        "rpm": 1450.0,
        "torque_nm": 45.2,
        "health_score": 94.0,
        "anomaly_score": 0.08,
        "source": "simulator",
        "schema_version": "1.0",
    }
    record = TelemetryRecord(**payload)
    assert record.machine_id == "M01"
    assert record.power_kw == 7.8
    assert record.energy_kwh == 125.6
    assert record.machine_state == MachineState.RUNNING
    assert record.production_count == 120
    assert record.production_delta == 2
    assert record.cycle_time_sec == 30.0
    assert record.health_score == 94.0
    assert record.anomaly_score == 0.08
    assert record.source == TelemetrySource.SIMULATOR
    assert record.schema_version == "1.0"


def test_minimal_telemetry_record():
    """Verify that a record with only core required fields succeeds with optionals as None."""
    now_utc = datetime.now(timezone.utc)
    record = TelemetryRecord(
        timestamp=now_utc,
        machine_id="M02",
        power_kw=4.5,
        energy_kwh=88.2,
        machine_state=MachineState.IDLE,
    )
    assert record.machine_id == "M02"
    assert record.power_kw == 4.5
    assert record.energy_kwh == 88.2
    assert record.machine_state == MachineState.IDLE
    # Optionals should default to None
    assert record.production_count is None
    assert record.production_delta is None
    assert record.cycle_time_sec is None
    assert record.voltage_v is None
    assert record.current_a is None
    assert record.temperature_c is None
    assert record.vibration is None
    assert record.rpm is None
    assert record.health_score is None
    assert record.anomaly_score is None
    # Sensible metadata defaults
    assert record.source == TelemetrySource.SIMULATOR
    assert record.schema_version == "1.0"


# ==============================================================================
# 2. NEGATIVE VALIDATION TESTS
# ==============================================================================

def test_invalid_machine_state():
    """Verify that an unrecognized machine state raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state="UNKNOWN_STATE",
        )
    assert "machine_state" in str(exc_info.value)


def test_negative_power_rejected():
    """Verify negative power_kw is rejected."""
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=-0.1,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
        )


def test_negative_energy_rejected():
    """Verify negative energy_kwh is rejected."""
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=-1.0,
            machine_state=MachineState.RUNNING,
        )


def test_negative_production_rejected():
    """Verify negative production count and delta are rejected."""
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            production_count=-1,
        )
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            production_delta=-5,
        )


def test_negative_vibration_rejected():
    """Verify negative vibration is rejected."""
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            vibration=-0.01,
        )


def test_negative_rpm_rejected():
    """Verify negative RPM is rejected."""
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            rpm=-50.0,
        )


def test_invalid_health_score():
    """Verify health score must strictly be in [0.0, 100.0]."""
    # Negative health score
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            health_score=-1.0,
        )
    # Exceeds 100
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            health_score=100.1,
        )


def test_invalid_anomaly_score():
    """Verify anomaly score must strictly be in [0.0, 1.0]."""
    # Negative anomaly score
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            anomaly_score=-0.01,
        )
    # Exceeds 1.0
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M01",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
            anomaly_score=1.05,
        )


def test_invalid_machine_id():
    """Verify empty or whitespace-only machine_id is rejected."""
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
        )
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="   ",
            power_kw=5.0,
            energy_kwh=10.0,
            machine_state=MachineState.RUNNING,
        )


# ==============================================================================
# 3. EDGE CASES & BOUNDARY TESTS
# ==============================================================================

def test_machine_id_whitespace_stripping():
    """Verify machine_id whitespace is stripped automatically."""
    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="  M03  ",
        power_kw=5.0,
        energy_kwh=10.0,
        machine_state=MachineState.RUNNING,
    )
    assert record.machine_id == "M03"


def test_edge_case_zero_power_and_production():
    """Verify 0.0 kW power and 0 production count are valid."""
    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=0.0,
        energy_kwh=10.0,
        production_count=0,
        cycle_time_sec=0.0,
        machine_state=MachineState.SLEEP,
    )
    assert record.power_kw == 0.0
    assert record.production_count == 0
    assert record.cycle_time_sec == 0.0
    assert record.machine_state == MachineState.SLEEP


def test_edge_case_boundary_scores():
    """Verify exact boundaries (0 and 100 for health, 0.0 and 1.0 for anomaly)."""
    record_min = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=2.0,
        energy_kwh=10.0,
        machine_state=MachineState.DEGRADED,
        health_score=0.0,
        anomaly_score=0.0,
    )
    assert record_min.health_score == 0.0
    assert record_min.anomaly_score == 0.0

    record_max = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=15.0,
        energy_kwh=10.0,
        machine_state=MachineState.OVERLOAD,
        health_score=100.0,
        anomaly_score=1.0,
    )
    assert record_max.health_score == 100.0
    assert record_max.anomaly_score == 1.0


def test_edge_case_subzero_temperatures():
    """Verify sub-zero temperatures (e.g. cold storage or freezing ambient) are accepted."""
    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M04",
        power_kw=4.0,
        energy_kwh=20.0,
        machine_state=MachineState.RUNNING,
        temperature_c=-15.5,
    )
    assert record.temperature_c == -15.5

    # But physically impossible extreme temperature (> 300C) should be rejected
    with pytest.raises(ValidationError):
        TelemetryRecord(
            timestamp=datetime.now(timezone.utc),
            machine_id="M04",
            power_kw=4.0,
            energy_kwh=20.0,
            machine_state=MachineState.RUNNING,
            temperature_c=500.0,
        )


def test_distinction_missing_vs_zero_production():
    """
    Ensure the schema clearly preserves the distinction between:
    - production_count is None (sensor unavailable / non-production machine)
    - production_count == 0 (machine active but 0 parts produced)
    This distinction is crucial for downstream SEC calculation.
    """
    rec_none = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=3.0,
        energy_kwh=12.0,
        machine_state=MachineState.IDLE,
        production_count=None,
    )
    assert rec_none.production_count is None

    rec_zero = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=3.0,
        energy_kwh=12.0,
        machine_state=MachineState.IDLE,
        production_count=0,
    )
    assert rec_zero.production_count == 0
    assert rec_none.production_count != rec_zero.production_count


# ==============================================================================
# 4. TIMESTAMP & TIMEZONE HANDLING
# ==============================================================================

def test_timezone_normalization():
    """Verify timezone offsets (e.g. IST +05:30) are normalized to UTC."""
    ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = datetime(2026, 10, 2, 15, 30, 0, tzinfo=ist)
    record = TelemetryRecord(
        timestamp=dt_ist,
        machine_id="M01",
        power_kw=5.0,
        energy_kwh=10.0,
        machine_state=MachineState.RUNNING,
    )
    assert record.timestamp.tzinfo == timezone.utc
    assert record.timestamp.hour == 10  # 15:30 IST is 10:00 UTC


def test_naive_timestamp_conversion():
    """Verify naive datetimes are interpreted and stamped with UTC timezone."""
    naive_dt = datetime(2026, 10, 2, 10, 0, 0)
    record = TelemetryRecord(
        timestamp=naive_dt,
        machine_id="M01",
        power_kw=5.0,
        energy_kwh=10.0,
        machine_state=MachineState.RUNNING,
    )
    assert record.timestamp.tzinfo is not None
    assert record.timestamp.tzinfo == timezone.utc


# ==============================================================================
# 5. JSON ROUND-TRIP SERIALIZATION & MQTT COMPATIBILITY
# ==============================================================================

def test_json_roundtrip_serialization():
    """Verify dict -> Pydantic -> JSON string -> Pydantic preserves all types."""
    original = TelemetryRecord(
        timestamp=datetime(2026, 10, 2, 10, 30, 0, tzinfo=timezone.utc),
        machine_id="M01",
        power_kw=8.2,
        energy_kwh=150.4,
        voltage_v=412.5,
        current_a=13.1,
        production_count=250,
        production_delta=1,
        cycle_time_sec=28.5,
        machine_state=MachineState.RUNNING,
        temperature_c=48.2,
        vibration=0.15,
        rpm=1480.0,
        torque_nm=39.0,
        health_score=96.5,
        anomaly_score=0.03,
        source=TelemetrySource.GATEWAY,
        schema_version="1.0",
    )

    # Serialize to JSON (as would be published to MQTT topic 'factory/M01/telemetry')
    json_str = original.model_dump_json()
    assert isinstance(json_str, str)
    raw_dict = json.loads(json_str)
    assert raw_dict["machine_id"] == "M01"
    assert raw_dict["machine_state"] == "RUNNING"
    assert raw_dict["source"] == "gateway"

    # Deserialize back from JSON (as MQTT subscriber or API would do)
    restored = TelemetryRecord.model_validate_json(json_str)
    assert restored.timestamp == original.timestamp
    assert restored.machine_id == original.machine_id
    assert restored.power_kw == original.power_kw
    assert restored.energy_kwh == original.energy_kwh
    assert restored.machine_state == original.machine_state
    assert restored.production_count == original.production_count
    assert restored.health_score == original.health_score
    assert restored.source == original.source


# ==============================================================================
# 6. FASTAPI ENDPOINT INGESTION INTEGRATION
# ==============================================================================

def test_api_ingest_valid_telemetry():
    """Verify POST /telemetry returns 201 Created and validated response."""
    payload = {
        "timestamp": "2026-10-02T10:30:00Z",
        "machine_id": "M01",
        "power_kw": 7.8,
        "energy_kwh": 125.6,
        "machine_state": "RUNNING",
        "production_count": 120,
    }
    response = client.post("/telemetry", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] in ("received", "accepted")
    assert data["machine_id"] == "M01"
    assert "2026-10-02T10:30:00" in data["timestamp"]


def test_api_ingest_invalid_telemetry_returns_422():
    """Verify POST /telemetry returns 422 Unprocessable Entity for invalid telemetry."""
    # Invalid: negative power
    invalid_payload = {
        "timestamp": "2026-10-02T10:30:00Z",
        "machine_id": "M01",
        "power_kw": -5.0,
        "energy_kwh": 125.6,
        "machine_state": "RUNNING",
    }
    response = client.post("/telemetry", json=invalid_payload)
    assert response.status_code == 422
