"""
Machine Utilization and Operational State Duration Analytics.
Explicitly classifies productive vs non-productive industrial machine states.
Productive: RUNNING, DEGRADED, OVERLOAD.
Non-productive: IDLE, SLEEP.
"""

from typing import List, Dict, Tuple, Optional
from database.schemas import TelemetryRecord, MachineState

PRODUCTIVE_STATES = {
    MachineState.RUNNING,
    MachineState.DEGRADED,
    MachineState.OVERLOAD,
}

NON_PRODUCTIVE_STATES = {
    MachineState.IDLE,
    MachineState.SLEEP,
}


def calculate_utilization(productive_time_sec: float, total_observed_time_sec: float) -> float:
    """
    Calculates operational utilization percentage.
    Formula: Utilization (%) = (Productive Time / Total Observed Time) * 100.
    """
    if total_observed_time_sec <= 0:
        return 0.0
    pct = (productive_time_sec / total_observed_time_sec) * 100.0
    return round(min(100.0, max(0.0, pct)), 2)


def calculate_state_durations(
    records: List[TelemetryRecord],
) -> Tuple[Dict[str, float], float, float]:
    """
    Calculates exact duration (in hours) spent in each machine state across telemetry intervals.
    Uses actual timestamp differences: dt = t_i - t_{i-1}.

    Returns:
        Tuple of (durations_by_state_hours, total_hours, productive_hours)
    """
    durations_sec: Dict[str, float] = {
        MachineState.RUNNING.value: 0.0,
        MachineState.IDLE.value: 0.0,
        MachineState.SLEEP.value: 0.0,
        MachineState.DEGRADED.value: 0.0,
        MachineState.OVERLOAD.value: 0.0,
    }

    if len(records) < 2:
        return {k: 0.0 for k in durations_sec}, 0.0, 0.0

    total_sec = 0.0
    productive_sec = 0.0

    for i in range(1, len(records)):
        prev = records[i - 1]
        curr = records[i]
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        if dt <= 0:
            continue

        state_val = curr.machine_state.value if hasattr(curr.machine_state, "value") else str(curr.machine_state)
        durations_sec[state_val] = durations_sec.get(state_val, 0.0) + dt
        total_sec += dt

        curr_state_enum = curr.machine_state if isinstance(curr.machine_state, MachineState) else MachineState(state_val)
        if curr_state_enum in PRODUCTIVE_STATES:
            productive_sec += dt

    durations_hours = {k: round(v / 3600.0, 4) for k, v in durations_sec.items()}
    total_hours = round(total_sec / 3600.0, 4)
    productive_hours = round(productive_sec / 3600.0, 4)

    return durations_hours, total_hours, productive_hours
