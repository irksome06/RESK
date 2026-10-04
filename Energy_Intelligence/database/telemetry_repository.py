"""
Unified Industrial Telemetry Repository.
Encapsulates all database operations, query patterns, time-series indexing,
and idempotent duplicate handling for MQTT QoS 1 message retries.
Serves as the single persistence layer for both FastAPI and MQTT ingestion.
"""

import logging
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, desc

from database.database import SessionLocal, get_db_context
from database.models import TelemetryDB
from database.schemas import TelemetryRecord, FactorySnapshot, MachineState

logger = logging.getLogger("database.repository")


class TelemetryRepository:
    """
    Data Access Object (DAO) for industrial machine telemetry.
    Supports session injection for FastAPI request lifecycles and
    automatic isolated sessions for background MQTT callbacks.
    """

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or SessionLocal

    def save_telemetry(
        self,
        record: TelemetryRecord,
        db: Optional[Session] = None,
    ) -> Tuple[TelemetryRecord, bool]:
        """
        Persists a canonical TelemetryRecord to the database.
        Idempotent: If a record with identical (machine_id, timestamp) already exists,
        rolls back safely and returns (existing_record, False) without raising unhandled errors.

        Returns:
            Tuple[TelemetryRecord, bool]: (record, is_new)
        """
        if db is not None:
            return self._save_with_session(record, db)
        else:
            with get_db_context() as session:
                return self._save_with_session(record, session)

    def _save_with_session(
        self,
        record: TelemetryRecord,
        db: Session,
    ) -> Tuple[TelemetryRecord, bool]:
        # Check first or insert with savepoint / integrity error handling
        db_model = TelemetryDB.from_telemetry_record(record)
        try:
            # Use a savepoint so that an integrity error rollback does not corrupt the parent session
            with db.begin_nested():
                db.add(db_model)
                db.flush()
            return db_model.to_telemetry_record(), True
        except IntegrityError:
            # Duplicate (machine_id, timestamp) detected
            logger.info(
                "Duplicate telemetry detected for %s at %s; skipping duplicate insertion",
                record.machine_id,
                record.timestamp,
            )
            # Fetch and return the previously persisted record
            existing = (
                db.query(TelemetryDB)
                .filter(
                    TelemetryDB.machine_id == record.machine_id,
                    TelemetryDB.timestamp == record.timestamp,
                )
                .first()
            )
            if existing:
                return existing.to_telemetry_record(), False
            return record, False

    def save_telemetry_batch(
        self,
        records: List[TelemetryRecord],
        db: Optional[Session] = None,
    ) -> int:
        """
        Persists a batch of telemetry records, skipping duplicates safely.
        Returns the number of newly inserted records.
        """
        if db is not None:
            return self._save_batch_with_session(records, db)
        else:
            with get_db_context() as session:
                return self._save_batch_with_session(records, session)

    def _save_batch_with_session(
        self,
        records: List[TelemetryRecord],
        db: Session,
    ) -> int:
        inserted_count = 0
        for rec in records:
            _, is_new = self._save_with_session(rec, db)
            if is_new:
                inserted_count += 1
        return inserted_count

    def get_recent_telemetry(
        self,
        limit: int = 50,
        machine_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> List[TelemetryRecord]:
        """
        Retrieves recent telemetry in reverse chronological order (newest first).
        Optionally filtered by machine_id.
        """
        bounded_limit = min(max(1, limit), 1000)

        def _execute(session: Session) -> List[TelemetryRecord]:
            query = session.query(TelemetryDB)
            if machine_id:
                clean_id = machine_id.strip()
                query = query.filter(TelemetryDB.machine_id == clean_id)
            query = query.order_by(desc(TelemetryDB.timestamp)).limit(bounded_limit)
            return [row.to_telemetry_record() for row in query.all()]

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)

    def get_telemetry_window(
        self,
        machine_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        db: Optional[Session] = None,
    ) -> List[TelemetryRecord]:
        """
        Retrieves telemetry records within [start_time, end_time] in chronological order (oldest first).
        Optionally filtered by machine_id. Optimized for deterministic time-series energy analytics.
        """
        def _execute(session: Session) -> List[TelemetryRecord]:
            query = session.query(TelemetryDB)
            if machine_id:
                clean_id = machine_id.strip()
                query = query.filter(TelemetryDB.machine_id == clean_id)
            if start_time:
                query = query.filter(TelemetryDB.timestamp >= start_time)
            if end_time:
                query = query.filter(TelemetryDB.timestamp <= end_time)
            query = query.order_by(TelemetryDB.timestamp.asc())
            return [row.to_telemetry_record() for row in query.all()]

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)

    def get_latest_telemetry(
        self,
        machine_id: str,
        db: Optional[Session] = None,
    ) -> Optional[TelemetryRecord]:
        """
        Retrieves the single most recent telemetry record for a specified machine.
        """
        clean_id = machine_id.strip()

        def _execute(session: Session) -> Optional[TelemetryRecord]:
            row = (
                session.query(TelemetryDB)
                .filter(TelemetryDB.machine_id == clean_id)
                .order_by(desc(TelemetryDB.timestamp))
                .first()
            )
            return row.to_telemetry_record() if row else None

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)

    def get_known_machine_ids(
        self,
        db: Optional[Session] = None,
    ) -> List[str]:
        """
        Returns sorted list of distinct machine_ids observed in the database.
        """
        def _execute(session: Session) -> List[str]:
            rows = session.query(TelemetryDB.machine_id).distinct().all()
            return sorted([r[0] for r in rows if r[0]])

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)

    def get_machine_telemetry_count(
        self,
        machine_id: str,
        db: Optional[Session] = None,
    ) -> int:
        """
        Returns total records persisted for a specific machine.
        """
        clean_id = machine_id.strip()

        def _execute(session: Session) -> int:
            return (
                session.query(func.count(TelemetryDB.id))
                .filter(TelemetryDB.machine_id == clean_id)
                .scalar()
                or 0
            )

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)

    def count_telemetry(
        self,
        db: Optional[Session] = None,
    ) -> int:
        """
        Returns total number of telemetry records in the persistent database.
        """
        def _execute(session: Session) -> int:
            return session.query(func.count(TelemetryDB.id)).scalar() or 0

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)

    def clear_all(
        self,
        db: Optional[Session] = None,
    ) -> int:
        """
        Removes all telemetry records (primarily used for test teardown).
        """
        def _execute(session: Session) -> int:
            deleted = session.query(TelemetryDB).delete()
            return deleted

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)

    def get_factory_snapshot(
        self,
        db: Optional[Session] = None,
    ) -> FactorySnapshot:
        """
        Derives an instantaneous aggregate summary from the latest observation of each machine.
        Uses subquery grouping to execute in a single SQL operation.
        """
        def _execute(session: Session) -> FactorySnapshot:
            # Subquery to find max timestamp per machine
            subq = (
                session.query(
                    TelemetryDB.machine_id.label("m_id"),
                    func.max(TelemetryDB.timestamp).label("max_ts"),
                )
                .group_by(TelemetryDB.machine_id)
                .subquery()
            )

            # Join to get full records for those max timestamps
            latest_rows = (
                session.query(TelemetryDB)
                .join(
                    subq,
                    and_(
                        TelemetryDB.machine_id == subq.c.m_id,
                        TelemetryDB.timestamp == subq.c.max_ts,
                    ),
                )
                .all()
            )

            if not latest_rows:
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

            records = [r.to_telemetry_record() for r in latest_rows]

            running = sum(1 for r in records if r.machine_state == MachineState.RUNNING)
            idle = sum(1 for r in records if r.machine_state == MachineState.IDLE)
            sleep = sum(1 for r in records if r.machine_state == MachineState.SLEEP)
            degraded = sum(1 for r in records if r.machine_state == MachineState.DEGRADED)
            overload = sum(1 for r in records if r.machine_state == MachineState.OVERLOAD)

            total_power = round(sum(r.power_kw for r in records), 3)

            prod_values = [r.production_count for r in records if r.production_count is not None]
            total_production = sum(prod_values) if prod_values else 0

            latest_ts = max(r.timestamp for r in records)

            return FactorySnapshot(
                timestamp=latest_ts,
                machines_seen=len(records),
                machines_running=running,
                machines_idle=idle,
                machines_sleep=sleep,
                machines_degraded=degraded,
                machines_overload=overload,
                total_power_kw=total_power,
                total_production=total_production,
            )

        if db is not None:
            return _execute(db)
        with get_db_context() as session:
            return _execute(session)


# Singleton repository instance
telemetry_repo = TelemetryRepository()


def ingest_telemetry_record(
    record: TelemetryRecord,
    db: Optional[Session] = None,
) -> Tuple[TelemetryRecord, bool]:
    """
    Unified Ingestion Function.
    Invoked identically by POST /telemetry and the MQTTSubscriber background callback.
    Persists to PostgreSQL/database with duplicate protection.
    """
    return telemetry_repo.save_telemetry(record, db=db)
