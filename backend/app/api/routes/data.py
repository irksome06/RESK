from fastapi import APIRouter, Query
from app.services.demo_data import build_timeseries
from app.services.analytics import baseline

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/timeseries")
def timeseries(hours: int = Query(24, ge=6, le=168)):
    df = build_timeseries(hours)
    return {"data": df.to_dict("records")}


@router.get("/overview")
def overview():
    df = build_timeseries(24)
    b = baseline(df)
    return {
        "plant": "Aurora Manufacturing Plant",
        "status": "Operational",
        "last_sync": df["timestamp"].iloc[-1],
        **b,
        "monthly_savings_inr": 284500,
        "carbon_intensity": 0.71,
        "active_assets": 18,
    }
