"""
Industrial Energy Baseline API Endpoints (Phase 8.1 V2).
Provides:
1. Production-aware baseline energy prediction (expected kWh) given operating context without power_kw.
2. Deterministic energy deviation calculation comparing actual vs expected energy.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from database.schemas import (
    BaselinePredictionRequest,
    BaselinePredictionResponse,
    EnergyDeviationRequest,
    EnergyDeviationResponse,
)
from ml.baseline import predict_expected_energy
from ml.train import calculate_energy_deviation

logger = logging.getLogger("api.baseline")

router = APIRouter(prefix="/baseline", tags=["Baseline"])


@router.post("/predict", response_model=BaselinePredictionResponse, status_code=status.HTTP_200_OK)
def predict_baseline(request: BaselinePredictionRequest):
    """
    Predicts expected electrical energy consumption (kWh) over the observation interval
    given operating conditions and production context.

    Answers: "Given what this machine produced and how it operated, how much energy would we normally expect it to consume?"
    Does NOT require power_kw or energy_kwh.
    """
    try:
        features = request.model_dump()
        # Convert enum value to string if needed
        if "machine_state" in features and hasattr(features["machine_state"], "value"):
            features["machine_state"] = features["machine_state"].value
        elif "machine_state" in features:
            features["machine_state"] = str(features["machine_state"])

        result = predict_expected_energy(features)

        return BaselinePredictionResponse(
            expected_energy_kwh=result["expected_energy_kwh"],
            model_name=result["model_name"],
            model_version=result["model_version"],
            features_used=result["features_used"],
            status=result["status"],
        )
    except Exception as e:
        logger.error("Error during baseline prediction: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Baseline prediction failed: {str(e)}",
        )


@router.post("/deviation", response_model=EnergyDeviationResponse, status_code=status.HTTP_200_OK)
def evaluate_deviation(request: EnergyDeviationRequest):
    """
    Computes deterministic energy deviation between actual and expected baseline energy:
    energy_deviation = actual_energy - expected_energy
    deviation_pct = (actual_energy - expected_energy) / expected_energy * 100
    """
    try:
        res = calculate_energy_deviation(
            actual_energy_kwh=request.actual_energy_kwh,
            expected_energy_kwh=request.expected_energy_kwh,
        )
        return EnergyDeviationResponse(**res)
    except Exception as e:
        logger.error("Error during energy deviation calculation: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Energy deviation calculation failed: {str(e)}",
        )
