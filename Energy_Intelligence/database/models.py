"""
SQLAlchemy ORM Models for Industrial Telemetry and Machine Assets.
Optimized for time-series industrial queries with composite machine+timestamp indexes,
timestamp range indexes, and unique constraints for MQTT QoS 1 duplicate delivery prevention.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    UniqueConstraint,
    Index,
)
from database.database import Base
from database.schemas import TelemetryRecord, TelemetrySource
from simulator.machine_states import MachineState


class TelemetryDB(Base):
    """
    Persistent time-series telemetry table.
    Stores high-frequency electrical, kinematic, thermal, and production observations.
    """
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    machine_id = Column(String(50), nullable=False, index=True)

    # Core electrical power & energy registers
    power_kw = Column(Float, nullable=False)
    energy_kwh = Column(Float, nullable=False)
    machine_state = Column(String(50), nullable=False, index=True)

    # Production metrics
    production_count = Column(Integer, nullable=True)
    production_delta = Column(Integer, nullable=True)
    cycle_time_sec = Column(Float, nullable=True)

    # Condition & sensor diagnostics
    voltage_v = Column(Float, nullable=True)
    current_a = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    vibration = Column(Float, nullable=True)
    rpm = Column(Float, nullable=True)
    torque_nm = Column(Float, nullable=True)
    health_score = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)

    # Metadata
    source = Column(String(50), default="simulator")
    schema_version = Column(String(20), default="1.0")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # Idempotency constraint: guarantees duplicate MQTT QoS 1 retries do not create duplicate rows
        UniqueConstraint("machine_id", "timestamp", name="uq_telemetry_machine_timestamp"),
        # Primary index pattern for time-series queries (e.g. M01 between t_start and t_end)
        Index("ix_telemetry_machine_timestamp", "machine_id", "timestamp"),
        # Index on timestamp for global chronological sorting & sliding window queries
        Index("ix_telemetry_timestamp_desc", timestamp.desc()),
        # Index for machine state filtering (e.g. finding idle / degraded periods)
        Index("ix_telemetry_state_machine", "machine_state", "machine_id"),
    )

    @classmethod
    def from_telemetry_record(cls, record: TelemetryRecord) -> "TelemetryDB":
        """Factory constructor converting validated Pydantic TelemetryRecord to ORM model."""
        ts = record.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        state_val = record.machine_state.value if hasattr(record.machine_state, "value") else str(record.machine_state)
        src_val = record.source.value if hasattr(record.source, "value") else str(record.source)

        return cls(
            timestamp=ts,
            machine_id=record.machine_id,
            power_kw=record.power_kw,
            energy_kwh=record.energy_kwh,
            machine_state=state_val,
            production_count=record.production_count,
            production_delta=record.production_delta,
            cycle_time_sec=record.cycle_time_sec,
            voltage_v=record.voltage_v,
            current_a=record.current_a,
            temperature_c=record.temperature_c,
            vibration=record.vibration,
            rpm=record.rpm,
            torque_nm=record.torque_nm,
            health_score=record.health_score,
            anomaly_score=record.anomaly_score,
            source=src_val,
            schema_version=record.schema_version or "1.0",
        )

    def to_telemetry_record(self) -> TelemetryRecord:
        """Converts persistent ORM model to validated Pydantic TelemetryRecord."""
        ts = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        state_enum = MachineState.RUNNING
        try:
            state_enum = MachineState(self.machine_state)
        except ValueError:
            pass

        src_enum = TelemetrySource.SIMULATOR
        try:
            src_enum = TelemetrySource(self.source)
        except ValueError:
            pass

        return TelemetryRecord(
            timestamp=ts,
            machine_id=self.machine_id,
            power_kw=self.power_kw,
            energy_kwh=self.energy_kwh,
            machine_state=state_enum,
            production_count=self.production_count,
            production_delta=self.production_delta,
            cycle_time_sec=self.cycle_time_sec,
            voltage_v=self.voltage_v,
            current_a=self.current_a,
            temperature_c=self.temperature_c,
            vibration=self.vibration,
            rpm=self.rpm,
            torque_nm=self.torque_nm,
            health_score=self.health_score,
            anomaly_score=self.anomaly_score,
            source=src_enum,
            schema_version=self.schema_version or "1.0",
        )


class Machine(Base):
    """
    Asset master register.
    Stores static machine engineering specifications.
    """
    __tablename__ = "machines"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    rated_power_kw = Column(Float, default=7.5)
    nominal_uph = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
