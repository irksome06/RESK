"""
Energy Baseline analytics.
Calculates historical deterministic SEC baselines and expected energy benchmarks.
Implemented in Phase 8.
"""

from typing import List, Optional
import numpy as np


def calculate_deterministic_baseline_sec(historical_secs: List[float]) -> Optional[float]:
    valid = [sec for sec in historical_secs if sec is not None and sec > 0]
    if not valid:
        return None
    return float(np.mean(valid))
