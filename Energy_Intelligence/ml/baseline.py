"""
Phase 8.1 Industrial Energy Baseline Inference Service (V2).
Production-Aware Expected Energy Baseline Modeling.

Answers:
"Given what this machine produced and how it operated, how much energy would we normally expect it to consume?"
Does NOT use power_kw, energy_kwh, or current_a as model features.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import joblib

from ml.preprocessing import ALL_FEATURE_COLUMNS, NUMERIC_FEATURES, CATEGORICAL_FEATURES, EXCLUDED_FEATURES
from ml.train import train_and_select_baseline, calculate_energy_deviation

logger = logging.getLogger("ml.baseline")

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
V2_MODEL_PATH = os.path.join(MODELS_DIR, "energy_baseline_v2_production_aware.joblib")
DEFAULT_MODEL_PATH = os.path.join(MODELS_DIR, "energy_baseline.joblib")
DEFAULT_METADATA_PATH = os.path.join(MODELS_DIR, "energy_baseline_metadata.json")


class EnergyBaselineService:
    """
    Inference service for production-aware energy baseline modeling (V2).
    Predicts expected interval energy (kWh) given contemporaneous machine conditions.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        metadata_path: str = DEFAULT_METADATA_PATH,
    ):
        if model_path is None:
            # Prefer V2 model if present, otherwise default
            if os.path.exists(V2_MODEL_PATH):
                self.model_path = V2_MODEL_PATH
            else:
                self.model_path = DEFAULT_MODEL_PATH
        else:
            self.model_path = model_path

        self.metadata_path = metadata_path
        self.pipeline = None
        self.metadata = {}
        self._load_or_train()

    def _load_or_train(self) -> None:
        """Loads persistent model and metadata, or trains if missing."""
        if os.path.exists(self.model_path) and os.path.exists(self.metadata_path):
            try:
                self.pipeline = joblib.load(self.model_path)
                with open(self.metadata_path, "r") as f:
                    self.metadata = json.load(f)
                logger.info(
                    "Loaded energy baseline model: %s (version: %s, samples: %d)",
                    self.metadata.get("selected_model", "Unknown"),
                    self.metadata.get("model_version", "v2_production_aware"),
                    self.metadata.get("total_samples", 0),
                )
                return
            except Exception as e:
                logger.warning("Failed to load baseline model artifact (%s). Retraining...", e)

        # Train and save if not found
        logger.info("Training fresh baseline V2 model...")
        summary = train_and_select_baseline(save_artifacts=True)
        self.pipeline = joblib.load(self.model_path)
        self.metadata = summary

    def predict_expected_energy(
        self,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Predicts expected interval energy consumption (kWh) given operating and production context.

        Args:
            features: Dictionary containing operating conditions
                      (machine_id, machine_state, production_delta, production_rate, rpm, etc.)
                      Note: power_kw and energy_kwh are IGNORED.

        Returns:
            Dictionary with expected_energy_kwh, model_name, model_version, and features used.
        """
        if self.pipeline is None:
            self._load_or_train()

        dt = float(features.get("dt_seconds", 2.0))
        prod_delta = float(features.get("production_delta", 0.0))

        # Support both 'production_rate' and 'production_rate_units_per_hour'
        prod_rate = features.get("production_rate")
        if prod_rate is None:
            prod_rate = features.get("production_rate_units_per_hour")
        if prod_rate is None:
            prod_rate = round(prod_delta / (dt / 3600.0), 2) if dt > 0 else 0.0

        # Support both 'hour_of_day' and 'hour'
        hour_val = features.get("hour_of_day")
        if hour_val is None:
            hour_val = features.get("hour", 12.0)

        # Build feature record with purely production and operating parameters (NO power_kw / energy_kwh)
        row: Dict[str, Any] = {
            "production_delta": float(prod_delta),
            "production_rate": float(prod_rate),
            "rpm": float(features.get("rpm", 1450.0)),
            "torque_nm": float(features.get("torque_nm", 0.0)),
            "temperature_c": float(features.get("temperature_c", 50.0)),
            "vibration": float(features.get("vibration", 0.18)),
            "health_score": float(features.get("health_score", 100.0)),
            "anomaly_score": float(features.get("anomaly_score", 0.0)),
            "hour_of_day": float(hour_val),
            "day_of_week": float(features.get("day_of_week", 2.0)),
            "dt_seconds": float(dt),
            "machine_state": str(features.get("machine_state", "RUNNING")),
            "machine_id": str(features.get("machine_id", "M01")),
        }

        # Convert to single-row DataFrame for pipeline
        df_input = pd.DataFrame([row])[ALL_FEATURE_COLUMNS]

        # Predict
        raw_pred = float(self.pipeline.predict(df_input)[0])
        expected_kwh = round(max(0.0, raw_pred), 6)

        return {
            "expected_energy_kwh": expected_kwh,
            "model_name": self.metadata.get("selected_model", "LinearRegression"),
            "model_version": self.metadata.get("model_version", "v2_production_aware"),
            "features_used": row,
            "status": "OK",
        }

    def evaluate_deviation(
        self,
        actual_energy_kwh: float,
        expected_energy_kwh: float,
    ) -> Dict[str, Any]:
        """Calculates deterministic energy deviation comparing actual vs expected."""
        return calculate_energy_deviation(actual_energy_kwh, expected_energy_kwh)


# Singleton service instance
baseline_service = EnergyBaselineService()


def predict_expected_energy(features: Dict[str, Any]) -> Dict[str, Any]:
    """Public functional API for baseline prediction."""
    return baseline_service.predict_expected_energy(features)
