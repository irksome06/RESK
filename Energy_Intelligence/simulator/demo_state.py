"""
Demo State Tracker for Smart Manufacturing Demonstration.
Tracks operational status, elapsed time, telemetry counts, and active scenario phases
for observability via GET /demo/status and the Streamlit dashboard.
Maintains the authoritative contiguous telemetry window for cross-module reconciliation.
"""

import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from simulator.scenarios import ScenarioPhase
from simulator.config import settings
from database.database import check_db_connected
from database.schemas import TelemetryRecord
from api.telemetry_store import telemetry_store


class DemoStateManager:
    """
    Thread-safe state manager for live factory demonstration runs.
    Maintains active demo telemetry records and authoritative analysis window.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.is_running: bool = False
        self.start_time: Optional[float] = None
        self.elapsed_seconds: float = 0.0
        self.telemetry_count: int = 0
        self.latest_timestamp: Optional[datetime] = None
        self.machines_active: int = 4
        self.current_phase: str = ScenarioPhase.PHASE_A_NORMAL.value
        self.mqtt_connected: bool = False
        self.last_run_timestamp: Optional[datetime] = None

        # Authoritative demo analysis window and in-memory contiguous records
        self.window_start_time: Optional[datetime] = None
        self.window_end_time: Optional[datetime] = None
        self.active_demo_records: Dict[str, List[TelemetryRecord]] = {
            "M01": [], "M02": [], "M03": [], "M04": []
        }
        self.active_demo_snapshot: Optional[Dict[str, Any]] = None

    def start_demo(self, start_ts: Optional[datetime] = None) -> None:
        """Marks the start of a demonstration scenario and clears previous run buffer."""
        with self._lock:
            self.is_running = True
            self.start_time = time.time()
            self.elapsed_seconds = 0.0
            self.current_phase = ScenarioPhase.PHASE_A_NORMAL.value
            self.window_start_time = start_ts
            self.window_end_time = None
            self.active_demo_records = {"M01": [], "M02": [], "M03": [], "M04": []}
            self.active_demo_snapshot = None
            self.telemetry_count = 0

    def reset(self) -> None:
        """Resets demonstration state and clears active demo records to clean state."""
        with self._lock:
            self.is_running = False
            self.start_time = None
            self.elapsed_seconds = 0.0
            self.current_phase = ScenarioPhase.PHASE_A_NORMAL.value
            self.window_start_time = None
            self.window_end_time = None
            self.latest_timestamp = None
            self.active_demo_records = {"M01": [], "M02": [], "M03": [], "M04": []}
            self.active_demo_snapshot = None
            self.telemetry_count = 0

    def update_phase(self, phase: str) -> None:
        """Updates the current scenario phase."""
        with self._lock:
            self.current_phase = phase
            if self.start_time:
                self.elapsed_seconds = round(time.time() - self.start_time, 2)

    def record_telemetry_record(self, record: TelemetryRecord) -> None:
        """Appends validated record to the active demo memory buffer."""
        with self._lock:
            m_id = record.machine_id
            if m_id not in self.active_demo_records:
                self.active_demo_records[m_id] = []
            self.active_demo_records[m_id].append(record)
            self.telemetry_count += 1
            if self.window_start_time is None:
                self.window_start_time = record.timestamp
            else:
                self.window_start_time = min(self.window_start_time, record.timestamp)
            self.window_end_time = record.timestamp
            self.latest_timestamp = record.timestamp
            if self.start_time:
                self.elapsed_seconds = round(time.time() - self.start_time, 2)

    def record_telemetry(self, count: int = 1, latest_ts: Optional[datetime] = None) -> None:
        """Records telemetry ingestion progress count."""
        with self._lock:
            self.telemetry_count += count
            if latest_ts:
                self.latest_timestamp = latest_ts
            if self.start_time:
                self.elapsed_seconds = round(time.time() - self.start_time, 2)

    def stop_demo(self, end_ts: Optional[datetime] = None) -> None:
        """Marks the completion of a demonstration scenario and fixes window_end_time."""
        with self._lock:
            self.is_running = False
            if self.start_time:
                self.elapsed_seconds = round(time.time() - self.start_time, 2)
            self.window_end_time = end_ts or self.latest_timestamp or datetime.now(timezone.utc)
            self.last_run_timestamp = self.window_end_time

    def set_mqtt_status(self, connected: bool) -> None:
        """Updates MQTT connection status."""
        with self._lock:
            self.mqtt_connected = connected

    def has_active_demo_data(self) -> bool:
        """Returns True if authoritative in-memory demo records exist."""
        with self._lock:
            return any(len(recs) >= 2 for recs in self.active_demo_records.values())

    def get_demo_records(self, machine_id: Optional[str] = None) -> List[TelemetryRecord]:
        """
        Retrieves contiguous in-memory demo records.
        Sorted chronologically.
        """
        with self._lock:
            if machine_id:
                recs = list(self.active_demo_records.get(machine_id, []))
                recs.sort(key=lambda r: r.timestamp)
                return recs
            all_recs = []
            for recs in self.active_demo_records.values():
                all_recs.extend(recs)
            all_recs.sort(key=lambda r: r.timestamp)
            return all_recs

    def get_demo_records_dict(self) -> Dict[str, List[TelemetryRecord]]:
        """Retrieves in-memory demo records grouped by machine ID."""
        with self._lock:
            result = {}
            for m_id, recs in self.active_demo_records.items():
                sorted_recs = list(recs)
                sorted_recs.sort(key=lambda r: r.timestamp)
                result[m_id] = sorted_recs
            return result

    def set_active_demo_records(self, records: List[TelemetryRecord]) -> None:
        """Stores demo records in-memory grouped by machine ID."""
        with self._lock:
            self.active_demo_records = {"M01": [], "M02": [], "M03": [], "M04": []}
            for r in records:
                if r.machine_id in self.active_demo_records:
                    self.active_demo_records[r.machine_id].append(r)
                else:
                    self.active_demo_records[r.machine_id] = [r]
            for m_id in self.active_demo_records:
                self.active_demo_records[m_id].sort(key=lambda x: x.timestamp)
            if records:
                timestamps = [r.timestamp for r in records]
                self.window_start_time = min(timestamps)
                self.window_end_time = max(timestamps)
                self.latest_timestamp = self.window_end_time

    def set_active_demo_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Stores the authoritative demo analytics snapshot for global sharing."""
        with self._lock:
            self.active_demo_snapshot = snapshot

    def get_active_demo_snapshot(self) -> Optional[Dict[str, Any]]:
        """Retrieves active demo snapshot if available."""
        with self._lock:
            return self.active_demo_snapshot

    def get_active_demo_window(self) -> Dict[str, Any]:
        """Returns the authoritative temporal window for the active demo."""
        with self._lock:
            start_str = self.window_start_time.strftime("%H:%M:%S") if self.window_start_time else "N/A"
            end_str = self.window_end_time.strftime("%H:%M:%S") if self.window_end_time else "N/A"
            dur = 0.0
            if self.window_start_time and self.window_end_time:
                dur = max(0.0, (self.window_end_time - self.window_start_time).total_seconds())
            return {
                "start_time": start_str,
                "end_time": end_str,
                "duration_seconds": round(dur, 1),
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Derives comprehensive demo health and progress status.
        Falls back to persistent database and telemetry store if idle.
        """
        with self._lock:
            is_connected, _ = check_db_connected()
            effective_count = self.telemetry_count
            effective_ts = self.latest_timestamp

            # Fallback to store if demo runner has not recorded in memory
            if effective_count == 0:
                store_count = telemetry_store.count()
                if store_count > 0:
                    effective_count = store_count
                    latest_rec = telemetry_store.get_recent(limit=1)
                    if latest_rec:
                        effective_ts = latest_rec[0].timestamp

            # Determine status label
            status_label = "RUNNING" if self.is_running else ("COMPLETED" if effective_count > 0 else "IDLE")

            return {
                "status": status_label,
                "running": self.is_running,
                "elapsed_time_seconds": self.elapsed_seconds,
                "telemetry_count": effective_count,
                "latest_telemetry_timestamp": effective_ts.isoformat() if effective_ts else None,
                "machines_active": self.machines_active,
                "current_scenario_phase": self.current_phase,
                "database_connected": is_connected,
                "mqtt_connected": self.mqtt_connected,
                "demo_mode": getattr(settings, "DEBUG", True),
            }


# Global singleton instance
demo_state = DemoStateManager()
