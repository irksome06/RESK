from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest


def baseline(df: pd.DataFrame) -> dict:
    mean = float(df["load_kw"].mean())
    std = float(df["load_kw"].std() or 1)
    latest = float(df["load_kw"].iloc[-1])
    energy_kwh = float(df["grid_kw"].sum())
    return {
        "avg_load_kw": round(mean, 1),
        "peak_load_kw": round(float(df["load_kw"].max()), 1),
        "latest_load_kw": round(latest, 1),
        "load_std_kw": round(std, 1),
        "energy_kwh": round(energy_kwh, 1),
        "baseline_method": "rolling mean + standard deviation",
    }


def detect_anomalies(df: pd.DataFrame) -> list[dict]:
    features = df[["load_kw", "temperature_c", "production_units"]]
    model = IsolationForest(contamination=0.12, random_state=42)
    predictions = model.fit_predict(features)
    scores = model.decision_function(features)
    output = []
    for row, pred, score in zip(df.to_dict("records"), predictions, scores):
        if pred == -1:
            output.append(
                {
                    "timestamp": row["timestamp"],
                    "load_kw": round(float(row["load_kw"]), 1),
                    "severity": "High" if score < -0.12 else "Medium",
                    "score": round(float(score), 3),
                    "message": "Load profile deviates from the learned operating pattern.",
                }
            )
    return output[-8:]
