"""
Database Engine, Session Lifecycle, and Connection Pooling Configuration.
Provides SQLAlchemy 2.x ORM engine, session factories, FastAPI dependency (get_db),
independent thread-safe context manager (get_db_context) for MQTT background workers,
and automatic resilient SQLite fallback if local PostgreSQL daemon is unavailable.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from simulator.config import settings

logger = logging.getLogger("database.database")

Base = declarative_base()


def _resolve_engine():
    """
    Creates the SQLAlchemy engine based on configuration.
    If PostgreSQL URL is configured but PostgreSQL daemon is offline,
    gracefully falls back to SQLite to ensure zero test/demo disruptions.
    """
    target_url = settings.DATABASE_URL

    if target_url.startswith("postgresql"):
        try:
            # Fast connection probe to verify PostgreSQL availability (1s timeout)
            probe_engine = create_engine(
                target_url,
                connect_args={"connect_timeout": 1},
                pool_pre_ping=True,
            )
            with probe_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to PostgreSQL at %s", target_url.split("@")[-1])
            # Create production-grade pooled engine
            return create_engine(
                target_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=1800,
            ), target_url
        except Exception as e:
            fallback_url = "sqlite:///./energy_intelligence.db"
            logger.warning(
                "PostgreSQL at %s is unavailable (%s). "
                "Falling back to local SQLite engine: %s",
                target_url.split("@")[-1] if "@" in target_url else target_url,
                type(e).__name__,
                fallback_url,
            )
            fallback_engine = create_engine(
                fallback_url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
            return fallback_engine, fallback_url
    else:
        # Direct SQLite or other database URL
        sqlite_engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False} if "sqlite" in target_url else {},
            pool_pre_ping=True,
        )
        return sqlite_engine, target_url


# Initialize active engine and session factory
engine, active_db_url = _resolve_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None) -> None:
    """
    Initializes all database tables registered under Base.metadata.
    Called explicitly during application startup and test suite setups.
    """
    import database.models  # noqa: F401
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    logger.info("Database schema initialized on %s", eng.url)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI request-scoped database dependency.
    Yields an independent session per HTTP request, commits on success,
    rolls back on exception, and guarantees connection return to pool.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Thread-safe context manager for background workers (e.g. MQTT subscriber).
    Creates an isolated short-lived session, commits transactions, and handles rollbacks.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connected() -> Tuple[bool, str]:
    """
    Executes a health-check query against the database engine.
    Returns (is_connected: bool, dialect_or_error: str).
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        dialect = "postgresql" if "postgresql" in str(engine.url) else "sqlite"
        return True, dialect
    except Exception as e:
        return False, str(e)


# Initialize tables on module load
try:
    init_db()
except Exception as init_err:
    logger.warning("Could not auto-initialize database tables: %s", init_err)
