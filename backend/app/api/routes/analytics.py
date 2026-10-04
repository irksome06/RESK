from fastapi import APIRouter, Query
from app.services.demo_data import build_timeseries
from app.services.analytics import baseline, detect_anomalies

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/baseline")
def baseline_endpoint(hours: int = Query(24, ge=6, le=168)):
    return baseline(build_timeseries(hours))


@router.get("/anomalies")
def anomalies(hours: int = Query(24, ge=6, le=168)):
    return {"anomalies": detect_anomalies(build_timeseries(hours))}
