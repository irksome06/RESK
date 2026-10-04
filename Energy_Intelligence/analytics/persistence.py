"""
Phase 9 Persistent Energy Deviation Detector.
Detects persistent above-baseline energy consumption across consecutive intervals:
- Eliminates single-interval noise/spikes from generating false alarms.
- Uses configurable thresholds (default: +15.0% for 3 consecutive intervals).
- Statuses: NORMAL, ABOVE_BASELINE, PERSISTENT_ABOVE_BASELINE, BELOW_BASELINE.
"""

from typing import List, Dict, Any, Optional


class PersistentDeviationDetector:
    """
    Deterministic detector for persistent energy deviations.
    Guarantees transparent, threshold-based classification without black-box alerts.
    """

    def __init__(
        self,
        threshold_pct: float = 15.0,
        consecutive_intervals: int = 3,
    ):
        """
        Args:
            threshold_pct: Percentage threshold above/below expected baseline (default: 15.0%).
                           In simulator normal RUNNING mode, power noise is ~4%.
                           15% threshold reliably detects sustained degradation (+25%) or overload (+40%).
            consecutive_intervals: Minimum consecutive intervals required to declare persistence (default: 3).
        """
        self.threshold_pct = float(threshold_pct)
        self.consecutive_intervals = int(consecutive_intervals)

    def evaluate_intervals(
        self,
        interval_deviations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Scans an ordered chronological sequence of interval deviations.

        Returns:
            Dict containing:
                - overall_status: NORMAL, ABOVE_BASELINE, PERSISTENT_ABOVE_BASELINE, BELOW_BASELINE
                - max_consecutive_above: int
                - is_persistent: bool
                - threshold_pct: float
                - consecutive_threshold: int
        """
        if not interval_deviations:
            return {
                "overall_status": "NORMAL",
                "max_consecutive_above": 0,
                "current_consecutive_above": 0,
                "is_persistent": False,
                "threshold_pct": self.threshold_pct,
                "consecutive_threshold": self.consecutive_intervals,
            }

        max_consecutive_above = 0
        current_consecutive_above = 0
        current_consecutive_below = 0

        for item in interval_deviations:
            dev_pct = float(item.get("deviation_pct", 0.0))

            if dev_pct > self.threshold_pct:
                current_consecutive_above += 1
                current_consecutive_below = 0
                if current_consecutive_above > max_consecutive_above:
                    max_consecutive_above = current_consecutive_above
            elif dev_pct < -self.threshold_pct:
                current_consecutive_below += 1
                current_consecutive_above = 0
            else:
                current_consecutive_above = 0
                current_consecutive_below = 0

        is_persistent = current_consecutive_above >= self.consecutive_intervals

        if is_persistent:
            status = "PERSISTENT_ABOVE_BASELINE"
        elif current_consecutive_above > 0:
            status = "ABOVE_BASELINE"
        elif current_consecutive_below >= self.consecutive_intervals:
            status = "BELOW_BASELINE"
        elif current_consecutive_below > 0:
            status = "BELOW_BASELINE"
        else:
            status = "NORMAL"

        return {
            "overall_status": status,
            "max_consecutive_above": max_consecutive_above,
            "current_consecutive_above": current_consecutive_above,
            "is_persistent": is_persistent,
            "threshold_pct": self.threshold_pct,
            "consecutive_threshold": self.consecutive_intervals,
        }


# Default detector singleton
persistence_detector = PersistentDeviationDetector(threshold_pct=15.0, consecutive_intervals=3)


def detect_persistent_deviation(
    interval_deviations: List[Dict[str, Any]],
    threshold_pct: float = 15.0,
    consecutive_intervals: int = 3,
) -> Dict[str, Any]:
    """Functional convenience API for persistent deviation detection."""
    detector = PersistentDeviationDetector(
        threshold_pct=threshold_pct,
        consecutive_intervals=consecutive_intervals,
    )
    return detector.evaluate_intervals(interval_deviations)
