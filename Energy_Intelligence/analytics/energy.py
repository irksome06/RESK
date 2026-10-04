"""
Energy Consumption and Operational State Energy Breakdown Analytics.
Implements cumulative meter delta validation, non-monotonic meter reset detection,
interval-accurate power integration fallback, and granular state-by-state energy allocation.
"""

from typing import List, Optional, Tuple, Dict
from database.schemas import TelemetryRecord, MachineState, StateEnergyBreakdown


def calculate_energy_consumption(
    records: List[TelemetryRecord],
) -> Tuple[Optional[float], str, List[str]]:
    """
    Computes total active electrical energy consumed over a telemetry window.

    Rules:
    - Primary: Difference between last and first cumulative `energy_kwh`.
      Strictly checks monotonicity: if energy_kwh decreases at any point,
      flags INVALID_NON_MONOTONIC_ENERGY and returns None.
    - Secondary: If `energy_kwh` register is unavailable, performs trapezoidal
      power integration: E = Σ ((P_{i-1} + P_i) / 2) × (dt / 3600).
    - Never blends both methods; documents calculation method explicitly.

    Returns:
        Tuple of (energy_kwh, calculation_method, warnings)
    """
    warnings: List[str] = []

    if len(records) < 2:
        return None, "INSUFFICIENT_DATA", ["At least two telemetry records are required"]

    has_meter = all(r.energy_kwh is not None for r in records)

    if has_meter:
        # Check monotonicity across consecutive samples
        for i in range(1, len(records)):
            prev_e = records[i - 1].energy_kwh
            curr_e = records[i].energy_kwh
            if curr_e < prev_e:
                warnings.append(
                    f"Non-monotonic energy meter detected between sample {i-1} ({prev_e} kWh) and {i} ({curr_e} kWh)"
                )
                return None, "INVALID_NON_MONOTONIC_ENERGY", warnings

        energy_consumed = round(records[-1].energy_kwh - records[0].energy_kwh, 4)
        return max(0.0, energy_consumed), "METER_DELTA", warnings

    # Fallback: Trapezoidal power integration
    total_energy_integrated = 0.0
    for i in range(1, len(records)):
        prev = records[i - 1]
        curr = records[i]
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        if dt <= 0:
            continue
        p_avg = (prev.power_kw + curr.power_kw) / 2.0
        total_energy_integrated += p_avg * (dt / 3600.0)

    warnings.append("Cumulative energy register missing; integrated instantaneous active power")
    return round(total_energy_integrated, 4), "POWER_INTEGRATION", warnings


def calculate_state_energy_breakdown(
    records: List[TelemetryRecord],
    total_energy_kwh: Optional[float] = None,
) -> StateEnergyBreakdown:
    """
    Allocates energy and time across industrial machine operational states:
    RUNNING, IDLE, SLEEP, DEGRADED, OVERLOAD.

    Calculates:
    - Running, Idle, Sleep, Degraded, and Overload energy (kWh).
    - Idle metrics (hours, average power in kW, % of total energy).
    - Sleep metrics (hours, % of total energy).
    """
    energy_by_state: Dict[str, float] = {
        MachineState.RUNNING.value: 0.0,
        MachineState.IDLE.value: 0.0,
        MachineState.SLEEP.value: 0.0,
        MachineState.DEGRADED.value: 0.0,
        MachineState.OVERLOAD.value: 0.0,
    }
    time_by_state_sec: Dict[str, float] = {k: 0.0 for k in energy_by_state}

    if len(records) < 2:
        return StateEnergyBreakdown()

    has_monotonic_meter = (
        all(r.energy_kwh is not None for r in records)
        and all(records[i].energy_kwh >= records[i - 1].energy_kwh for i in range(1, len(records)))
    )

    for i in range(1, len(records)):
        prev = records[i - 1]
        curr = records[i]
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        if dt <= 0:
            continue

        state_val = curr.machine_state.value if hasattr(curr.machine_state, "value") else str(curr.machine_state)
        time_by_state_sec[state_val] = time_by_state_sec.get(state_val, 0.0) + dt

        # Determine interval energy
        if has_monotonic_meter:
            interval_e = curr.energy_kwh - prev.energy_kwh
        else:
            p_avg = (prev.power_kw + curr.power_kw) / 2.0
            interval_e = p_avg * (dt / 3600.0)

        energy_by_state[state_val] = energy_by_state.get(state_val, 0.0) + interval_e

    # Round energy quantities
    running_e = round(energy_by_state[MachineState.RUNNING.value], 4)
    idle_e = round(energy_by_state[MachineState.IDLE.value], 4)
    sleep_e = round(energy_by_state[MachineState.SLEEP.value], 4)
    degraded_e = round(energy_by_state[MachineState.DEGRADED.value], 4)
    overload_e = round(energy_by_state[MachineState.OVERLOAD.value], 4)

    # Durations in hours
    running_h = round(time_by_state_sec[MachineState.RUNNING.value] / 3600.0, 4)
    idle_h = round(time_by_state_sec[MachineState.IDLE.value] / 3600.0, 4)
    sleep_h = round(time_by_state_sec[MachineState.SLEEP.value] / 3600.0, 4)
    degraded_h = round(time_by_state_sec[MachineState.DEGRADED.value] / 3600.0, 4)
    overload_h = round(time_by_state_sec[MachineState.OVERLOAD.value] / 3600.0, 4)

    # Total energy baseline for percentages
    effective_total = total_energy_kwh if total_energy_kwh is not None else sum(energy_by_state.values())

    idle_avg_pwr = round(idle_e / idle_h, 3) if idle_h > 0 else 0.0
    idle_pct = round((idle_e / effective_total) * 100.0, 2) if effective_total > 0 else 0.0
    sleep_pct = round((sleep_e / effective_total) * 100.0, 2) if effective_total > 0 else 0.0

    return StateEnergyBreakdown(
        running=running_e,
        idle=idle_e,
        sleep=sleep_e,
        degraded=degraded_e,
        overload=overload_e,
        running_energy_kwh=running_e,
        idle_energy_kwh=idle_e,
        sleep_energy_kwh=sleep_e,
        degraded_energy_kwh=degraded_e,
        overload_energy_kwh=overload_e,
        running_time_hours=running_h,
        idle_time_hours=idle_h,
        sleep_time_hours=sleep_h,
        degraded_time_hours=degraded_h,
        overload_time_hours=overload_h,
        idle_power_average_kw=idle_avg_pwr,
        idle_energy_pct=idle_pct,
        sleep_energy_pct=sleep_pct,
    )
