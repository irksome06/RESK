"""
Main FastAPI Application Entrypoint.
Provides REST APIs for industrial machine telemetry, asset inventories, and factory snapshots.
Backed by persistent database storage with unified MQTT subscriber ingestion via lifespan.
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from simulator.config import settings
from database.database import init_db, check_db_connected
from api.telemetry_store import ingest_telemetry_record
from api.telemetry import router as telemetry_router
from api.machines import router as machines_router
from api.metrics import router as metrics_router
from api.savings import router as savings_router
from api.copilot import router as copilot_router
from api.analytics import router as analytics_router
from api.baseline import router as baseline_router
from api.forecasting import router as forecasting_router
from api.deviation import router as deviation_router
from api.demo import router as demo_router
from simulator.demo_state import demo_state
from mqtt.subscriber import MQTTSubscriber

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    Ensures database tables are initialized, and starts MQTT background subscriber gracefully.
    """
    app.state.start_time = time.time()
    app.state.mqtt_subscriber = None
    app.state.mqtt_status = "OFFLINE"

    # Initialize persistent database schema
    try:
        init_db()
        logger.info("Database initialized successfully at application startup")
    except Exception as db_err:
        logger.warning("Database initialization warning during startup: %s", db_err)

    # Initialize MQTT subscriber
    try:
        subscriber = MQTTSubscriber(
            client_id=f"{settings.MQTT_CLIENT_ID}_fastapi_sub",
            on_telemetry=ingest_telemetry_record,
        )
        started = subscriber.start()
        if started:
            app.state.mqtt_subscriber = subscriber
            app.state.mqtt_status = "CONNECTED"
            demo_state.set_mqtt_status(True)
            logger.info("FastAPI connected to MQTT background subscriber successfully")
        else:
            app.state.mqtt_status = "OFFLINE"
            demo_state.set_mqtt_status(False)
            logger.warning("FastAPI started in standalone mode (MQTT broker offline)")
    except Exception as e:
        app.state.mqtt_status = "OFFLINE"
        demo_state.set_mqtt_status(False)
        logger.warning("Could not connect MQTT subscriber at startup: %s. Continuing in REST-only mode.", e)

    yield

    # Shutdown
    if app.state.mqtt_subscriber:
        try:
            app.state.mqtt_subscriber.stop()
            demo_state.set_mqtt_status(False)
            logger.info("FastAPI MQTT background subscriber stopped cleanly")
        except Exception as e:
            logger.warning("Error stopping MQTT subscriber: %s", e)


app = FastAPI(
    title="Energy & Production Intelligence Engine",
    description="Person 3: Production-aware energy intelligence module for Indian SMEs. "
                "Phase 6 persistent PostgreSQL database storage with REST and MQTT pipelines.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Person 4 Dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(telemetry_router)
app.include_router(machines_router)
app.include_router(metrics_router)
app.include_router(analytics_router)
app.include_router(baseline_router)
app.include_router(forecasting_router)
app.include_router(deviation_router)
app.include_router(savings_router)
app.include_router(copilot_router)
app.include_router(demo_router)


@app.get("/", tags=["Health"])
def root():
    """Service metadata and engine status."""
    return {
        "status": "online",
        "service": "person3-energy-intelligence",
        "engine": "Energy & Production Intelligence Engine",
        "version": "1.0.0",
        "env": settings.APP_ENV,
    }


@app.get("/health", tags=["Health"])
def health():
    """
    Health check endpoint reporting application and database connectivity status.
    """
    is_connected, _ = check_db_connected()
    db_status = "connected" if is_connected else "unavailable"
    return {
        "status": "healthy" if is_connected else "degraded",
        "database": db_status,
    }


@app.get("/ready", tags=["Health"])
def ready():
    """
    Readiness probe for deployment orchestrators.
    """
    is_connected, err = check_db_connected()
    if is_connected:
        return {"status": "ready", "database": "connected"}
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Database unavailable: {err}",
    )
