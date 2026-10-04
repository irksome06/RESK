"""
Phase 9 Short-Horizon Energy Forecasting API Endpoints.
Provides machine-level and factory-level multi-step energy consumption projections (1 to 5 intervals, 1-min each).
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from database.schemas import MachineForecastResponse, FactoryForecastResponse
from ml.forecasting import forecasting_service, DEFAULT_PROFILES
from api.telemetry_store import telemetry_store

logger = logging.getLogger("api.forecasting")

router = APIRouter(prefix="/forecast", tags=["Forecasting"])


@router.get(
    "/machine/{machine_id}",
    response_model=MachineForecastResponse,
    status_code=status.HTTP_200_OK,
)
def get_machine_forecast(
    machine_id: str,
    horizon_minutes: int = Query(default=5, ge=1, le=10, description="Forecasting horizon in 1-minute intervals (1-10)"),
):
    """
    Returns short-horizon future energy forecast for a specific machine.
    Forecast horizon: 1 to 5 minutes (default 5).
    Evaluated with recursive multi-step forecasting using trained model.
    """
    clean_id = machine_id.strip().upper()
    known_machines = set(DEFAULT_PROFILES.keys()) | set(telemetry_store.get_known_machine_ids())

    if clean_id not in known_machines and not clean_id.startswith("M"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id}' not found.",
        )

    try:
        # Check recent telemetry to find state & recent energy if available
        recent_records = telemetry_store.get_recent(limit=60, machine_id=clean_id)
        current_state = "RUNNING"
        recent_1min_energy = []

        if recent_records:
            current_state = recent_records[0].machine_state.value if hasattr(recent_records[0].machine_state, "value") else str(recent_records[0].machine_state)
            # Estimate recent 1-minute energy from available recent records
            if len(recent_records) >= 30:
                # 30 records at 2s = 1 minute
                chunk_size = 30
                for i in range(0, min(len(recent_records), 90), chunk_size):
                    chunk = recent_records[i:i + chunk_size]
                    e_sum = sum(getattr(r, "interval_energy_kwh", 0.0) or (r.power_kw * (r.dt_seconds if hasattr(r, "dt_seconds") and r.dt_seconds else 2.0) / 3600.0) for r in chunk)
                    recent_1min_energy.insert(0, round(e_sum, 6))

        result = forecasting_service.forecast_machine(
            machine_id=clean_id,
            recent_1min_energy=recent_1min_energy if len(recent_1min_energy) >= 3 else None,
            current_state=current_state,
            horizon_minutes=horizon_minutes,
        )

        return MachineForecastResponse(
            machine_id=result["machine_id"],
            horizon_minutes=result["horizon_minutes"],
            forecast_interval_minutes=result.get("forecast_interval_minutes", 1),
            forecast_energy_kwh=result["forecast_energy_kwh"],
            total_forecast_kwh=result.get("total_forecast_kwh"),
            model=result["model"],
            model_version=result["model_version"],
            status="OK",
        )
    except Exception as e:
        logger.error("Error generating machine forecast for %s: %s", clean_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting failed: {str(e)}",
        )


@router.get(
    "/factory",
    response_model=FactoryForecastResponse,
    status_code=status.HTTP_200_OK,
)
def get_factory_forecast(
    horizon_minutes: int = Query(default=5, ge=1, le=10, description="Forecasting horizon in 1-minute intervals (1-10)"),
):
    """
    Returns aggregated short-horizon energy forecast across all factory machines.
    """
    try:
        result = forecasting_service.forecast_factory(horizon_minutes=horizon_minutes)
        return FactoryForecastResponse(
            horizon_minutes=result["horizon_minutes"],
            forecast_interval_minutes=result.get("forecast_interval_minutes", 1),
            total_factory_forecast_kwh=result["total_factory_forecast_kwh"],
            factory_step_forecasts_kwh=result["factory_step_forecasts_kwh"],
            machine_forecasts=result["machine_forecasts"],
            model=result["model"],
            model_version=result["model_version"],
            status="OK",
        )
    except Exception as e:
        logger.error("Error generating factory forecast: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Factory forecast failed: {str(e)}",
        )
