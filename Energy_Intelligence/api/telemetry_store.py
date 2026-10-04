"""
Telemetry Storage & Unified Ingestion Adapter.
Bridges in-memory caching and persistent PostgreSQL/database storage via TelemetryRepository.
Preserves backwards compatibility with Phase 5 interfaces while establishing the database
as the authoritative persistent source of truth for Phase 6.
"""

import threading
from collections import deque, defaultdict
from datetime import datetime, timezone
from typing import List, Optional, Dict

from database.schemas import TelemetryRecord, FactorySnapshot, MachineState
from database.telemetry_repository import telemetry_repo


class InMemoryTelemetryStore:
    """
    Telemetry store supporting both in-memory bounded caching and persistent database synchronization.
    When persist_to_db=True, operations delegate authoritatively to the database repository.
    """

    def __init__(self, max_records: int = 1000, persist_to_db: bool = False):
        self.max_records = max_records
        self.persist_to_db = persist_to_db
        self._lock = threading.Lock()
        self._records: deque = deque(maxlen=max_records)
        self._latest_by_machine: Dict[str, TelemetryRecord] = {}
        self._counts_by_machine: Dict[str, int] = defaultdict(int)

    def add(self, record: TelemetryRecord) -> None:
        """Stores a validated TelemetryRecord in database and in-memory cache."""
        with self._lock:
            self._records.append(record)
            self._latest_by_machine[record.machine_id] = record
            self._counts_by_machine[record.machine_id] += 1

        if self.persist_to_db:
            telemetry_repo.save_telemetry(record)

    def get_recent(self, limit: int = 50, machine_id: Optional[str] = None) -> List[TelemetryRecord]:
        """
        Retrieves recent telemetry records in reverse chronological order (newest first).
        Queries the database if persist_to_db=True.
        """
        if self.persist_to_db:
            return telemetry_repo.get_recent_telemetry(limit=limit, machine_id=machine_id)

        with self._lock:
            if machine_id:
                clean_id = machine_id.strip()
                filtered = [r for r in reversed(self._records) if r.machine_id == clean_id]
                return filtered[:limit]
            else:
                return list(reversed(self._records))[:limit]

    def get_telemetry_window(
        self,
        machine_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TelemetryRecord]:
        """Retrieves records within [start_time, end_time] sorted chronologically."""
        if self.persist_to_db:
            return telemetry_repo.get_telemetry_window(machine_id=machine_id, start_time=start_time, end_time=end_time)

        with self._lock:
            records = list(self._records)
            if machine_id:
                clean_id = machine_id.strip()
                records = [r for r in records if r.machine_id == clean_id]
            if start_time:
                records = [r for r in records if r.timestamp >= start_time]
            if end_time:
                records = [r for r in records if r.timestamp <= end_time]
            records.sort(key=lambda r: r.timestamp)
            return records


    def get_latest(self, machine_id: str) -> Optional[TelemetryRecord]:
        """Fetches the single most recent record for a machine."""
        if self.persist_to_db:
            return telemetry_repo.get_latest_telemetry(machine_id)

        with self._lock:
            return self._latest_by_machine.get(machine_id.strip())

    def get_known_machine_ids(self) -> List[str]:
        """Returns sorted list of machine identifiers seen in telemetry."""
        if self.persist_to_db:
            return telemetry_repo.get_known_machine_ids()

        with self._lock:
            return sorted(list(self._latest_by_machine.keys()))

    def get_machine_telemetry_count(self, machine_id: str) -> int:
        """Returns total records ingested for a machine."""
        if self.persist_to_db:
            return telemetry_repo.get_machine_telemetry_count(machine_id)

        with self._lock:
            return self._counts_by_machine.get(machine_id.strip(), 0)

    def count(self) -> int:
        """Total records stored."""
        if self.persist_to_db:
            return telemetry_repo.count_telemetry()

        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        """Clears all records and indices in memory and database."""
        with self._lock:
            self._records.clear()
            self._latest_by_machine.clear()
            self._counts_by_machine.clear()

        if self.persist_to_db:
            telemetry_repo.clear_all()

    def get_factory_snapshot(self) -> FactorySnapshot:
        """
        Derives an instantaneous aggregate summary from the latest observation of each machine.
        """
        if self.persist_to_db:
            return telemetry_repo.get_factory_snapshot()

        with self._lock:
            latest_records = list(self._latest_by_machine.values())

            if not latest_records:
                return FactorySnapshot(
                    timestamp=datetime.now(timezone.utc),
                    machines_seen=0,
                    machines_running=0,
                    machines_idle=0,
                    machines_sleep=0,
                    machines_degraded=0,
                    machines_overload=0,
                    total_power_kw=0.0,
                    total_production=0,
                )

            running = sum(1 for r in latest_records if r.machine_state == MachineState.RUNNING)
            idle = sum(1 for r in latest_records if r.machine_state == MachineState.IDLE)
            sleep = sum(1 for r in latest_records if r.machine_state == MachineState.SLEEP)
            degraded = sum(1 for r in latest_records if r.machine_state == MachineState.DEGRADED)
            overload = sum(1 for r in latest_records if r.machine_state == MachineState.OVERLOAD)

            total_power = round(sum(r.power_kw for r in latest_records), 3)

            prod_values = [r.production_count for r in latest_records if r.production_count is not None]
            total_production = sum(prod_values) if prod_values else 0

            latest_ts = max(r.timestamp for r in latest_records)

            return FactorySnapshot(
                timestamp=latest_ts,
                machines_seen=len(latest_records),
                machines_running=running,
                machines_idle=idle,
                machines_sleep=sleep,
                machines_degraded=degraded,
                machines_overload=overload,
                total_power_kw=total_power,
                total_production=total_production,
            )


# Global singleton instance configured for persistent database backend
telemetry_store = InMemoryTelemetryStore(max_records=1000, persist_to_db=True)


def ingest_telemetry_record(record: TelemetryRecord) -> TelemetryRecord:
    """
    Unified ingestion pipeline function.
    Called identically by POST /telemetry and the MQTTSubscriber background callback.
    Persists record to the database repository and synchronizes the store.
    """
    telemetry_store.add(record)
    return record
