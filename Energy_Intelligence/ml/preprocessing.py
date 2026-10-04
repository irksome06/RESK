"""
Phase 8.1 Industrial Feature Engineering and Preprocessing Pipeline.
Production-Aware Expected Energy Baseline Modeling (V2).

CRITICAL DESIGN PRINCIPLE:
- The baseline answers: "Given what the machine produced and how it operated,
  how much energy would we normally expect it to consume?"
- EXCLUDES electrical proxies: power_kw, energy_kwh, current_a, voltage_v.
- LEARNS expected energy purely from: production throughput, machine state,
  operating mechanics (rpm, torque), thermal/vibration conditions, health,
  time of day, and interval duration.
- PREVENTS DATA LEAKAGE: All transformations fit strictly inside CV training folds.
- EXCLUDES INVALID METER RESETS: Monotonicity enforced per-machine.
"""

from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

from database.schemas import TelemetryRecord, MachineState

# EXPLICITLY EXCLUDED FEATURES (Electrical target proxies and cumulative meters)
EXCLUDED_FEATURES = [
    "power_kw",
    "energy_kwh",
    "interval_energy_kwh",
    "current_a",
    "voltage_v",
]

# PRODUCTION-AWARE OPERATING FEATURES (V2)
NUMERIC_FEATURES = [
    "production_delta",
    "production_rate",
    "rpm",
    "torque_nm",
    "temperature_c",
    "vibration",
    "health_score",
    "anomaly_score",
    "hour_of_day",
    "day_of_week",
    "dt_seconds",
]

CATEGORICAL_FEATURES = [
    "machine_state",
    "machine_id",
]

ALL_FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "interval_energy_kwh"


def extract_features_and_target_from_records(
    records: List[TelemetryRecord],
) -> pd.DataFrame:
    """
    Constructs a production-aware feature dataset from raw sequential TelemetryRecord instances.

    Target:
        interval_energy_kwh = energy_kwh[t] - energy_kwh[t-1]  (computed per machine)

    Exclusions:
        - The first record of each machine is dropped (no preceding baseline interval).
        - Non-monotonic meter readings (energy_kwh[t] < energy_kwh[t-1]) are excluded.
        - power_kw, energy_kwh, current_a, and voltage_v are excluded from modeling features.
    """
    if not records or len(records) < 2:
        return pd.DataFrame()

    # Sort records chronologically by machine
    df_raw = pd.DataFrame([r.model_dump() for r in records])
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
    df_raw.sort_values(by=["machine_id", "timestamp"], inplace=True)
    df_raw.reset_index(drop=True, inplace=True)

    rows: List[Dict[str, Any]] = []

    # Process consecutive intervals per machine
    for machine_id, group in df_raw.groupby("machine_id"):
        group = group.sort_values(by="timestamp").reset_index(drop=True)
        for i in range(1, len(group)):
            prev = group.iloc[i - 1]
            curr = group.iloc[i]

            dt = (curr["timestamp"] - prev["timestamp"]).total_seconds()
            if dt <= 0:
                continue

            # Compute target interval energy
            e_prev = prev["energy_kwh"]
            e_curr = curr["energy_kwh"]

            # Validate monotonicity: exclude invalid meter resets/drops
            if e_curr is None or e_prev is None:
                continue
            if e_curr < e_prev:
                # Meter reset or data corruption: exclude interval from training
                continue

            interval_energy = round(float(e_curr - e_prev), 6)

            # Features available at or over the interval
            prod_delta = curr["production_delta"] if curr["production_delta"] is not None else 0.0
            prod_rate = round(float(prod_delta) / (dt / 3600.0), 2) if dt > 0 else 0.0

            state_val = curr["machine_state"]
            if hasattr(state_val, "value"):
                state_val = state_val.value

            row = {
                "timestamp": curr["timestamp"],
                "machine_id": str(curr["machine_id"]),
                "machine_state": str(state_val),
                "production_delta": float(prod_delta),
                "production_rate": float(prod_rate),
                "production_rate_units_per_hour": float(prod_rate),  # backward compatibility alias
                "rpm": float(curr["rpm"]) if curr["rpm"] is not None else 0.0,
                "torque_nm": float(curr["torque_nm"]) if curr["torque_nm"] is not None else 0.0,
                "temperature_c": float(curr["temperature_c"]) if curr["temperature_c"] is not None else 25.0,
                "vibration": float(curr["vibration"]) if curr["vibration"] is not None else 0.0,
                "health_score": float(curr["health_score"]) if curr["health_score"] is not None else 100.0,
                "anomaly_score": float(curr["anomaly_score"]) if curr["anomaly_score"] is not None else 0.0,
                "hour_of_day": float(curr["timestamp"].hour),
                "day_of_week": float(curr["timestamp"].weekday()),
                "dt_seconds": float(dt),
                TARGET_COLUMN: interval_energy,
            }
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    df_out = pd.DataFrame(rows)
    # Global chronological ordering
    df_out.sort_values(by="timestamp", inplace=True)
    df_out.reset_index(drop=True, inplace=True)
    return df_out


def create_preprocessor() -> ColumnTransformer:
    """
    Creates an sklearn ColumnTransformer for production-aware baseline modeling.
    Numeric: Median imputation + StandardScaler.
    Categorical: OneHotEncoder with handle_unknown='ignore'.
    """
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            (
                "encoder",
                OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )

    return preprocessor
