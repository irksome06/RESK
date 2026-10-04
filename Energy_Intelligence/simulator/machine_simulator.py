"""
Realistic Physics-Inspired Industrial Machine Simulator.
Generates dynamically consistent, multi-machine industrial telemetry validating
against the Phase 2 TelemetryRecord schema without independent random values.
"""

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from database.schemas import TelemetryRecord, TelemetrySource
from simulator.machine_states import MachineState


@dataclass
class MachineProfile:
    """Static engineering specifications for a machine asset."""
    machine_id: str
    name: str
    rated_power_kw: float
    nominal_uph: float  # Units per hour in normal RUNNING mode
    nominal_rpm: float = 1450.0
    nominal_voltage_v: float = 415.0
    nominal_power_factor: float = 0.86
    nominal_temp_c: float = 50.0
    nominal_vibration: float = 0.18  # mm/s RMS
    idle_power_ratio: float = 0.18   # Fraction of rated power in IDLE (~18%)
    sleep_power_kw: float = 0.35     # Absolute low-power baseline in SLEEP
    thermal_time_constant_sec: float = 300.0  # Thermal inertia parameter
    degradation_sensitivity: float = 1.0


# Standard profiles for M01 through M04 with distinct characteristics
DEFAULT_PROFILES: Dict[str, MachineProfile] = {
    "M01": MachineProfile(
        machine_id="M01",
        name="CNC Milling Center 1",
        rated_power_kw=7.5,
        nominal_uph=120.0,
        nominal_rpm=1450.0,
        nominal_temp_c=50.0,
        nominal_vibration=0.18,
        idle_power_ratio=0.18,  # ~1.35 kW in IDLE
        sleep_power_kw=0.35,
    ),
    "M02": MachineProfile(
        machine_id="M02",
        name="Heavy Lathe 2",
        rated_power_kw=6.8,
        nominal_uph=100.0,
        nominal_rpm=1200.0,
        nominal_temp_c=48.0,
        nominal_vibration=0.16,
        idle_power_ratio=0.20,  # ~1.36 kW in IDLE
        sleep_power_kw=0.30,
    ),
    "M03": MachineProfile(
        machine_id="M03",
        name="Stamping Press 3",
        rated_power_kw=8.2,
        nominal_uph=130.0,
        nominal_rpm=1500.0,
        nominal_temp_c=52.0,
        nominal_vibration=0.20,
        idle_power_ratio=0.17,  # ~1.39 kW in IDLE
        sleep_power_kw=0.40,
    ),
    "M04": MachineProfile(
        machine_id="M04",
        name="Precision Grinder 4",
        rated_power_kw=5.5,
        nominal_uph=90.0,
        nominal_rpm=2800.0,
        nominal_temp_c=45.0,
        nominal_vibration=0.15,
        idle_power_ratio=0.19,  # ~1.05 kW in IDLE
        sleep_power_kw=0.25,
    ),
}


class SingleMachineSimulator:
    """
    Simulates a single industrial machine with coupled electro-thermal-mechanical physics.
    State transitions influence power demand, thermal buildup, vibration, component wear,
    and instantaneous production rates.
    """

    def __init__(
        self,
        profile: MachineProfile,
        seed: Optional[int] = None,
        initial_energy_kwh: float = 100.0,
        initial_production_count: int = 0,
        ambient_temp_c: float = 28.0,
    ):
        self.profile = profile
        self.rng = random.Random(seed)

        # Operational state
        self.state = MachineState.RUNNING
        self.ambient_temp_c = ambient_temp_c

        # Dynamic physical state variables (with inertia)
        self.cumulative_energy_kwh = float(initial_energy_kwh)
        self.cumulative_production_count = int(initial_production_count)
        self.fractional_production_buffer = 0.0

        self.current_temperature_c = profile.nominal_temp_c
        self.current_vibration = profile.nominal_vibration
        self.degradation_level = 0.0  # 0.0 = mint condition, 1.0 = severely worn
        self.overload_factor = 0.0    # 0.0 = normal, up to 0.40 in OVERLOAD
        self.health_score = 96.0      # 0.0 to 100.0
        self.anomaly_score = 0.04     # 0.0 to 1.0

        # Latest generated record cache
        self.last_record: Optional[TelemetryRecord] = None

    def set_state(self, new_state: MachineState) -> None:
        """Transitions machine to a new state."""
        self.state = new_state
        if new_state == MachineState.OVERLOAD:
            self.overload_factor = 0.35
        elif new_state != MachineState.DEGRADED:
            self.overload_factor = 0.0

    def trigger_degradation(self, level_increment: float = 0.20) -> None:
        """Induces progressive mechanical/thermal degradation."""
        self.state = MachineState.DEGRADED
        self.degradation_level = min(1.0, self.degradation_level + level_increment)

    def trigger_overload(self) -> None:
        """Induces severe electrical and mechanical overload."""
        self.state = MachineState.OVERLOAD
        self.overload_factor = 0.40

    def trigger_recovery(self) -> None:
        """Simulates maintenance or optimization intervention restoring normal operation."""
        self.state = MachineState.RUNNING
        self.overload_factor = 0.0
        # Inertial recovery: degradation level will decay toward 0.0 over subsequent steps

    def step(self, dt_seconds: float, timestamp: datetime) -> TelemetryRecord:
        """
        Advances machine physical state by dt_seconds and generates a validated TelemetryRecord.
        """
        # 1. State inertia & progression
        if self.state == MachineState.DEGRADED:
            # Gradual wear progression under degraded operation
            self.degradation_level = min(1.0, self.degradation_level + 0.002 * (dt_seconds / 1.0))
        elif self.state == MachineState.OVERLOAD:
            self.degradation_level = min(1.0, self.degradation_level + 0.005 * (dt_seconds / 1.0))
        elif self.state in (MachineState.RUNNING, MachineState.IDLE, MachineState.SLEEP):
            if self.degradation_level > 0.0:
                # Gradual recovery toward zero if maintenance occurred
                self.degradation_level = max(0.0, self.degradation_level - 0.02 * (dt_seconds / 1.0))

        # 2. Power Model (kW)
        # Power = Base(state) * LoadFactor * DegradationMultiplier + BoundedNoise
        noise_p = self.rng.uniform(-0.04, 0.04) * self.profile.rated_power_kw

        if self.state == MachineState.RUNNING:
            deg_p_mult = 1.0 + (0.22 * self.degradation_level)
            power_kw = (self.profile.rated_power_kw * 1.02 * deg_p_mult) + noise_p
        elif self.state == MachineState.IDLE:
            power_kw = (self.profile.rated_power_kw * self.profile.idle_power_ratio) + (noise_p * 0.25)
        elif self.state == MachineState.SLEEP:
            power_kw = self.profile.sleep_power_kw + (self.rng.uniform(-0.015, 0.015))
        elif self.state == MachineState.DEGRADED:
            deg_p_mult = 1.15 + (0.25 * self.degradation_level)
            power_kw = (self.profile.rated_power_kw * deg_p_mult) + noise_p
        elif self.state == MachineState.OVERLOAD:
            power_kw = (self.profile.rated_power_kw * (1.38 + self.overload_factor)) + (noise_p * 1.5)
        else:
            power_kw = self.profile.rated_power_kw

        power_kw = max(0.05, round(power_kw, 3))

        # 3. Energy Accumulation (kWh)
        # dt in hours = dt_seconds / 3600.0
        dt_hours = dt_seconds / 3600.0
        energy_increment = power_kw * dt_hours
        self.cumulative_energy_kwh += energy_increment
        energy_kwh = round(self.cumulative_energy_kwh, 5)

        # 4. Production Model
        # Units depend on state and degradation efficiency
        production_delta = 0
        cycle_time_sec = 0.0

        if self.state in (MachineState.IDLE, MachineState.SLEEP):
            effective_uph = 0.0
        elif self.state == MachineState.RUNNING:
            effective_uph = self.profile.nominal_uph * (1.0 - 0.15 * self.degradation_level)
        elif self.state == MachineState.DEGRADED:
            # Drop in throughput alongside increased power -> Higher SEC
            effective_uph = self.profile.nominal_uph * (0.85 - 0.25 * self.degradation_level)
        elif self.state == MachineState.OVERLOAD:
            # Overloaded machine runs slightly faster or stutters
            effective_uph = self.profile.nominal_uph * 1.04
        else:
            effective_uph = 0.0

        if effective_uph > 0.0:
            units_per_sec = effective_uph / 3600.0
            self.fractional_production_buffer += units_per_sec * dt_seconds

            if self.fractional_production_buffer >= 1.0:
                completed = int(math.floor(self.fractional_production_buffer))
                production_delta = completed
                self.fractional_production_buffer -= completed
                self.cumulative_production_count += completed
                cycle_time_sec = round(3600.0 / effective_uph, 2)

        # 5. Temperature Model with Thermal Inertia
        # Newton's Law of Cooling + Heat Generation
        # dT/dt = (Q_in - Q_out) / thermal_mass
        if self.state in (MachineState.RUNNING, MachineState.DEGRADED, MachineState.OVERLOAD):
            target_steady_temp = (
                self.profile.nominal_temp_c
                + (self.degradation_level * 18.0)
                + (self.overload_factor * 26.0)
            )
        else:
            # In IDLE or SLEEP, target relaxes toward ambient
            target_steady_temp = self.ambient_temp_c + (2.0 if self.state == MachineState.IDLE else 0.5)

        # Thermal inertia step
        cooling_rate = dt_seconds / self.profile.thermal_time_constant_sec
        thermal_diff = target_steady_temp - self.current_temperature_c
        thermal_noise = self.rng.uniform(-0.05, 0.05)
        self.current_temperature_c += (thermal_diff * min(1.0, cooling_rate * 2.5)) + thermal_noise
        temperature_c = round(self.current_temperature_c, 2)

        # 6. Vibration Model (mm/s RMS)
        vib_noise = self.rng.uniform(-0.015, 0.015)
        if self.state == MachineState.SLEEP:
            # Spindle/motor halted; vibration drops immediately to ambient floor
            self.current_vibration = round(0.004 + abs(vib_noise * 0.2), 3)
        elif self.state == MachineState.IDLE:
            target_vib = self.profile.nominal_vibration * 0.20
            self.current_vibration += (target_vib - self.current_vibration) * min(1.0, dt_seconds * 0.4) + vib_noise
            self.current_vibration = max(0.001, round(self.current_vibration, 3))
        elif self.state == MachineState.RUNNING:
            target_vib = self.profile.nominal_vibration * (1.0 + 0.5 * self.degradation_level)
            self.current_vibration += (target_vib - self.current_vibration) * min(1.0, dt_seconds * 0.4) + vib_noise
            self.current_vibration = max(0.001, round(self.current_vibration, 3))
        elif self.state == MachineState.DEGRADED:
            target_vib = self.profile.nominal_vibration * (2.2 + 2.4 * self.degradation_level)
            self.current_vibration += (target_vib - self.current_vibration) * min(1.0, dt_seconds * 0.4) + vib_noise
            self.current_vibration = max(0.001, round(self.current_vibration, 3))
        elif self.state == MachineState.OVERLOAD:
            target_vib = self.profile.nominal_vibration * 2.8
            self.current_vibration += (target_vib - self.current_vibration) * min(1.0, dt_seconds * 0.4) + vib_noise
            self.current_vibration = max(0.001, round(self.current_vibration, 3))
        else:
            target_vib = self.profile.nominal_vibration
            self.current_vibration += (target_vib - self.current_vibration) * min(1.0, dt_seconds * 0.4) + vib_noise
            self.current_vibration = max(0.001, round(self.current_vibration, 3))

        # 7. Rotational Speed (RPM) & Torque (Nm)
        rpm_noise = self.rng.uniform(-5.0, 5.0)
        if self.state == MachineState.SLEEP:
            rpm = 0.0
            torque_nm = 0.0
        elif self.state == MachineState.IDLE:
            rpm = max(0.0, 15.0 + rpm_noise)
            torque_nm = round(self.profile.rated_power_kw * 0.5, 2)
        elif self.state == MachineState.RUNNING:
            rpm = round(self.profile.nominal_rpm + rpm_noise, 1)
            torque_nm = round((9550.0 * power_kw) / max(1.0, rpm), 2)
        elif self.state == MachineState.DEGRADED:
            rpm = round((self.profile.nominal_rpm * (0.97 - 0.06 * self.degradation_level)) + (rpm_noise * 2), 1)
            torque_nm = round((9550.0 * power_kw) / max(1.0, rpm), 2)
        elif self.state == MachineState.OVERLOAD:
            rpm = round((self.profile.nominal_rpm * 0.95) + (rpm_noise * 3), 1)
            torque_nm = round((9550.0 * power_kw) / max(1.0, rpm), 2)
        else:
            rpm = self.profile.nominal_rpm
            torque_nm = 35.0

        # 8. Electrical Parameters: 3-Phase Voltage & Current
        voltage_v = round(self.profile.nominal_voltage_v + self.rng.uniform(-3.5, 3.5), 1)
        # 3-Phase: P = sqrt(3) * V * I * PF / 1000  =>  I = 1000 * P / (sqrt(3) * V * PF)
        denom = math.sqrt(3) * voltage_v * self.profile.nominal_power_factor
        current_a = round((1000.0 * power_kw) / max(1.0, denom), 2)

        # 9. Health Score (0-100) & Anomaly Score (0.0-1.0)
        # Deterministic, explainable physical wear formulation
        temp_excess = max(0.0, self.current_temperature_c - self.profile.nominal_temp_c)
        vib_excess = max(0.0, self.current_vibration - self.profile.nominal_vibration)

        health_penalties = (
            (35.0 * self.degradation_level)
            + (25.0 * self.overload_factor)
            + (0.4 * temp_excess)
            + (25.0 * vib_excess)
        )
        target_health = max(10.0, min(98.0, 97.0 - health_penalties))
        # Health score has inertia (cannot drop or jump instantly)
        self.health_score += (target_health - self.health_score) * min(1.0, dt_seconds * 0.15)
        health_score = round(max(0.0, min(100.0, self.health_score)), 1)

        # Anomaly score correlates with degradation, vibration, and thermal excess
        anomaly_metric = (
            (0.55 * self.degradation_level)
            + (0.45 * self.overload_factor)
            + min(0.3, vib_excess * 1.5)
            + min(0.2, temp_excess * 0.02)
        )
        target_anomaly = min(0.98, max(0.02, anomaly_metric + self.rng.uniform(-0.02, 0.02)))
        self.anomaly_score += (target_anomaly - self.anomaly_score) * min(1.0, dt_seconds * 0.2)
        anomaly_score = round(max(0.0, min(1.0, self.anomaly_score)), 2)

        # 10. Construct Canonical Telemetry Record
        record = TelemetryRecord(
            timestamp=timestamp,
            machine_id=self.profile.machine_id,
            power_kw=power_kw,
            energy_kwh=energy_kwh,
            machine_state=self.state,
            production_count=self.cumulative_production_count,
            production_delta=production_delta,
            cycle_time_sec=cycle_time_sec,
            voltage_v=voltage_v,
            current_a=current_a,
            temperature_c=temperature_c,
            vibration=self.current_vibration,
            rpm=rpm,
            torque_nm=torque_nm,
            health_score=health_score,
            anomaly_score=anomaly_score,
            source=TelemetrySource.SIMULATOR,
            schema_version="1.0",
        )
        self.last_record = record
        return record


class FactorySimulator:
    """
    Coordinates multi-machine simulation (M01, M02, M03, M04) across time.
    Provides deterministic stepping, scenario triggers, and reproducible datasets.
    """

    def __init__(
        self,
        machine_profiles: Optional[Dict[str, MachineProfile]] = None,
        seed: Optional[int] = 42,
        start_time: Optional[datetime] = None,
        ambient_temp_c: float = 28.0,
    ):
        self.master_seed = seed
        self.master_rng = random.Random(seed)

        self.current_sim_time = start_time or datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
        self.ambient_temp_c = ambient_temp_c

        profiles = machine_profiles or DEFAULT_PROFILES
        self.machines: Dict[str, SingleMachineSimulator] = {}

        for machine_id, profile in profiles.items():
            child_seed = self.master_rng.randint(1000, 999999) if seed is not None else None
            self.machines[machine_id] = SingleMachineSimulator(
                profile=profile,
                seed=child_seed,
                initial_energy_kwh=100.0,
                initial_production_count=0,
                ambient_temp_c=ambient_temp_c,
            )

    def get_machine(self, machine_id: str) -> SingleMachineSimulator:
        """Fetch individual machine simulator instance."""
        if machine_id not in self.machines:
            raise KeyError(f"Machine {machine_id} not found in factory simulation")
        return self.machines[machine_id]

    def set_machine_state(self, machine_id: str, state: MachineState) -> None:
        """Set machine state for an individual asset."""
        self.get_machine(machine_id).set_state(state)

    def trigger_degradation(self, machine_id: str, level_increment: float = 0.20) -> None:
        """Trigger progressive degradation on machine."""
        self.get_machine(machine_id).trigger_degradation(level_increment)

    def trigger_overload(self, machine_id: str) -> None:
        """Trigger overload on machine."""
        self.get_machine(machine_id).trigger_overload()

    def trigger_recovery(self, machine_id: str) -> None:
        """Trigger maintenance/optimization recovery on machine."""
        self.get_machine(machine_id).trigger_recovery()

    def step(self, dt_seconds: float = 1.0) -> List[TelemetryRecord]:
        """
        Advances the simulated factory clock by dt_seconds without sleep.
        Returns validated TelemetryRecord for each active machine in order.
        """
        self.current_sim_time += timedelta(seconds=dt_seconds)
        records = []
        for machine in self.machines.values():
            rec = machine.step(dt_seconds=dt_seconds, timestamp=self.current_sim_time)
            records.append(rec)
        return records

    def get_all_telemetry(self) -> List[TelemetryRecord]:
        """Returns the most recent telemetry records from all simulated machines."""
        return [m.last_record for m in self.machines.values() if m.last_record is not None]

    def run(self, steps: int, dt_seconds: float = 1.0) -> List[List[TelemetryRecord]]:
        """
        Runs batch deterministic simulation for dataset generation or ML training.
        """
        history = []
        for _ in range(steps):
            history.append(self.step(dt_seconds=dt_seconds))
        return history
