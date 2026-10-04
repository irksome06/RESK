"""
Production Output and Rate Analytics.
Computes throughput from cumulative piece registers and interval deltas.
Handles counter resets, irregular sampling intervals, and missing production data cleanly.
"""

from typing import List, Optional, Tuple
from database.schemas import TelemetryRecord


def calculate_production_metrics(
    records: List[TelemetryRecord],
    elapsed_hours: float,
) -> Tuple[Optional[int], Optional[float], List[str]]:
    """
    Computes total production units and production rate (units/hour).

    Rules:
    - Primary: Difference between last and first cumulative `production_count` if monotonic.
    - If counter reset detected (last < first): records warning "PRODUCTION_COUNTER_RESET"
      and attempts fallback to sum of `production_delta` if available.
    - If `production_count` is unavailable (None) on records, sums available `production_delta`.
    - If neither is available: returns (None, None, warnings).
    - Distinguishes 0 from None (0 = zero pieces produced, None = sensor unavailable).

    Returns:
        Tuple of (total_production_units, production_rate_units_per_hour, warnings)
    """
    warnings: List[str] = []

    if len(records) < 2:
        return None, None, ["Insufficient records to compute production throughput"]

    first = records[0]
    last = records[-1]

    # Check if cumulative counter is present
    has_first_count = first.production_count is not None
    has_last_count = last.production_count is not None

    if has_first_count and has_last_count:
        if last.production_count < first.production_count:
            warnings.append("PRODUCTION_COUNTER_RESET")
            # Check if production_delta is available across intervals
            deltas = [r.production_delta for r in records[1:] if r.production_delta is not None]
            if len(deltas) == len(records) - 1:
                total_prod = sum(deltas)
            else:
                return None, None, warnings
        else:
            total_prod = last.production_count - first.production_count
    else:
        # Check production deltas
        deltas = [r.production_delta for r in records[1:] if r.production_delta is not None]
        if deltas:
            total_prod = sum(deltas)
        else:
            warnings.append("PRODUCTION_UNAVAILABLE")
            return None, None, warnings

    rate = None
    if elapsed_hours > 0 and total_prod is not None:
        rate = round(total_prod / elapsed_hours, 2)

    return total_prod, rate, warnings
