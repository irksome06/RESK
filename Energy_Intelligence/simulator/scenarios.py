"""
Deterministic Industrial Demonstration Scenario Controller.
Orchestrates multi-phase operational transitions (Normal -> Idle -> Sleep -> Degraded -> Overload -> Recovery)
for demonstrations, verification, and hackathon presentation.
"""

from enum import Enum
from typing import Dict, List, Any
from datetime import datetime

from database.schemas import TelemetryRecord
from simulator.machine_states import MachineState
from simulator.machine_simulator import FactorySimulator


class ScenarioPhase(str, Enum):
    PHASE_A_NORMAL = "PHASE_A_NORMAL"
    PHASE_B_IDLE = "PHASE_B_IDLE"
    PHASE_C_SLEEP = "PHASE_C_SLEEP"
    PHASE_D_DEGRADED = "PHASE_D_DEGRADED"
    PHASE_E_OVERLOAD = "PHASE_E_OVERLOAD"
    PHASE_F_RECOVERY = "PHASE_F_RECOVERY"


class DemoScenarioController:
    """
    Coordinates factory progression through the canonical demo phases.
    Separates scenario orchestration from core machine physics.
    """

    def __init__(self, simulator: FactorySimulator):
        self.sim = simulator
        self.current_phase = ScenarioPhase.PHASE_A_NORMAL
        self.phase_history: List[Dict[str, Any]] = []

    def set_phase(self, phase: ScenarioPhase) -> None:
        """Applies machine state modifications corresponding to each phase."""
        self.current_phase = phase

        if phase == ScenarioPhase.PHASE_A_NORMAL:
            # All machines normal running
            for m_id in ("M01", "M02", "M03", "M04"):
                self.sim.set_machine_state(m_id, MachineState.RUNNING)

        elif phase == ScenarioPhase.PHASE_B_IDLE:
            # Person 1 observation: M01 becomes IDLE (production stops, idle power continues)
            self.sim.set_machine_state("M01", MachineState.IDLE)

        elif phase == ScenarioPhase.PHASE_C_SLEEP:
            # Person 1 optimization: M01 sleep command activated (deep power drop)
            self.sim.set_machine_state("M01", MachineState.SLEEP)

        elif phase == ScenarioPhase.PHASE_D_DEGRADED:
            # Person 2 anomaly: M03 experiences progressive mechanical degradation
            self.sim.trigger_degradation("M03", level_increment=0.35)

        elif phase == ScenarioPhase.PHASE_E_OVERLOAD:
            # Factory event: M02 experiences extreme electrical & mechanical overload
            self.sim.trigger_overload("M02")

        elif phase == ScenarioPhase.PHASE_F_RECOVERY:
            # Maintenance / Optimization: M03 repaired, M02 recovered to normal RUNNING
            self.sim.trigger_recovery("M03")
            self.sim.set_machine_state("M02", MachineState.RUNNING)

    def step_phase(self, steps: int = 1, dt_seconds: float = 1.0) -> List[List[TelemetryRecord]]:
        """Executes simulation steps within current phase."""
        phase_records = []
        for _ in range(steps):
            records = self.sim.step(dt_seconds=dt_seconds)
            phase_records.append(records)
        return phase_records

    def run_full_demo(self, steps_per_phase: int = 10, dt_seconds: float = 1.0) -> Dict[str, Any]:
        """
        Executes complete end-to-end 6-phase industrial scenario.
        Returns aggregated phase telemetry and summary metrics.
        """
        demo_log = {}
        ordered_phases = [
            ScenarioPhase.PHASE_A_NORMAL,
            ScenarioPhase.PHASE_B_IDLE,
            ScenarioPhase.PHASE_C_SLEEP,
            ScenarioPhase.PHASE_D_DEGRADED,
            ScenarioPhase.PHASE_E_OVERLOAD,
            ScenarioPhase.PHASE_F_RECOVERY,
        ]

        for phase in ordered_phases:
            self.set_phase(phase)
            records = self.step_phase(steps=steps_per_phase, dt_seconds=dt_seconds)
            demo_log[phase.value] = {
                "phase": phase.value,
                "step_count": steps_per_phase,
                "records": records,
            }

        return demo_log
