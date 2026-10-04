from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import sin
import numpy as np
import pandas as pd


def build_timeseries(hours: int = 24) -> pd.DataFrame:
    hours = max(6, min(hours, 168))
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    timestamps = [now - timedelta(hours=hours - 1 - i) for i in range(hours)]
    rows: list[dict] = []
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        shift_factor = 1.0 if 7 <= hour < 15 else (0.84 if 15 <= hour < 23 else 0.57)
        wave = 1.0 + 0.07 * sin(i / 2.4) + 0.025 * sin(i / 0.9)
        if hour in (10, 11, 12):
            wave *= 1.15
        if hour == 12 and i % 9 == 0:
            wave *= 1.24
        load_kw = max(220, 520 * shift_factor * wave)
        solar_kw = max(0, 155 * sin((hour - 6) / 12 * np.pi))
        import_kw = max(0, load_kw - solar_kw)
        tariff = 8.6 if 18 <= hour < 22 else (6.1 if 0 <= hour < 6 else 7.3)
        rows.append(
            {
                "timestamp": ts.isoformat(),
                "load_kw": round(load_kw, 1),
                "solar_kw": round(solar_kw, 1),
                "grid_kw": round(import_kw, 1),
                "tariff_inr_per_kwh": tariff,
                "production_units": round(load_kw / 3.35, 1),
                "temperature_c": round(24 + 5 * sin((hour - 7) / 24 * 2 * np.pi), 1),
            }
        )
    return pd.DataFrame(rows)


def maintenance_windows() -> list[dict]:
    return [
        {"asset": "CNC Line 02", "window": "02:00–03:00", "risk": "Medium", "reason": "Vibration trend 11% above baseline"},
        {"asset": "Compressor A", "window": "03:00–04:30", "risk": "Low", "reason": "Prefer off-peak tariff window"},
        {"asset": "Cooling Tower", "window": "05:00–06:00", "risk": "Medium", "reason": "Temperature drift detected"},
        {"asset": "Packaging Cell 04", "window": "23:00–00:00", "risk": "Low", "reason": "Production slack available"},
    ]
