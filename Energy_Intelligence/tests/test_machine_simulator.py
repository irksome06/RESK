"""
Phase 3 Machine Simulator Unit & Integration Tests.
Validates physical relationships, energy/production monotonicity, state transitions,
deterministic reproducibility, schema validation, and demo scenario progression.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest

# Ensure person3_energy_intelligence is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.schemas import TelemetryRecord, MachineState
from simulator.machine_simulator import FactorySimulator, SingleMachineSimulator, DEFAULT_PROFILES
from simulator.scenarios import DemoScenarioController, ScenarioPhase


# ==============================================================================
# 1. INITIALIZATION & SCHEMA COMPLIANCE
# ==============================================================================

def test_factory_simulator_initialization():
    """Verify FactorySimulator initializes M01 through M04 with distinct profiles."""
    sim = FactorySimulator(seed=42)
    assert set(sim.machines.keys()) == {"M01", "M02", "M03", "M04"}
    m01 = sim.get_machine("M01")
    m04 = sim.get_machine("M04")
    assert m01.profile.rated_power_kw == 7.5
    assert m04.profile.rated_power_kw == 5.5
    assert m01.profile.nominal_uph != m04.profile.nominal_uph


def test_step_schema_compatibility():
    """Verify every step output validates strictly as a TelemetryRecord."""
    sim = FactorySimulator(seed=100)
    records = sim.step(dt_seconds=1.0)
    assert len(records) == 4
    for r in records:
        assert isinstance(r, TelemetryRecord)
        assert r.machine_id in {"M01", "M02", "M03", "M04"}
        assert r.power_kw >= 0.0
        assert r.energy_kwh >= 0.0
        assert r.health_score is not None and 0.0 <= r.health_score <= 100.0
        assert r.anomaly_score is not None and 0.0 <= r.anomaly_score <= 1.0


# ==============================================================================
# 2. MONOTONICITY OF PHYSICAL REGISTERS
# ==============================================================================

def test_energy_and_production_monotonicity():
    """Verify cumulative energy and production counters never decrease over time."""
    sim = FactorySimulator(seed=42)
    prev_energies = {m_id: 0.0 for m_id in sim.machines}
    prev_counts = {m_id: 0 for m_id in sim.machines}

    for _ in range(50):
        records = sim.step(dt_seconds=2.0)
        for r in records:
            assert r.energy_kwh >= prev_energies[r.machine_id], "Energy meter decreased!"
            assert r.production_count is not None
            assert r.production_count >= prev_counts[r.machine_id], "Production counter decreased!"
            prev_energies[r.machine_id] = r.energy_kwh
            prev_counts[r.machine_id] = r.production_count


# ==============================================================================
# 3. STATE-SPECIFIC PHYSICAL BEHAVIOR
# ==============================================================================

def test_running_behavior():
    """Verify RUNNING state produces positive production and near-nominal power."""
    sim = FactorySimulator(seed=42)
    sim.set_machine_state("M01", MachineState.RUNNING)

    # Run for 60 seconds (1 minute)
    batch = [sim.step(dt_seconds=1.0)[0] for _ in range(60)]
    avg_power = sum(r.power_kw for r in batch) / len(batch)
    total_delta = sum(r.production_delta or 0 for r in batch)

    assert 7.0 <= avg_power <= 8.5, f"Unexpected RUNNING power for M01: {avg_power}"
    assert total_delta >= 1, f"Expected production in RUNNING mode: {total_delta}"
    assert batch[-1].machine_state == MachineState.RUNNING


def test_idle_behavior():
    """Verify IDLE state produces 0 units with power significantly lower than RUNNING."""
    sim = FactorySimulator(seed=42)
    sim.set_machine_state("M01", MachineState.IDLE)

    batch = [sim.step(dt_seconds=1.0)[0] for _ in range(30)]
    for r in batch:
        assert r.production_delta == 0
        assert r.machine_state == MachineState.IDLE
        # M01 rated is 7.5 kW; idle power is ~1.35 kW
        assert 1.0 <= r.power_kw <= 2.2, f"Idle power out of range: {r.power_kw}"
        assert r.rpm is not None and r.rpm < 50.0


def test_sleep_behavior():
    """Verify SLEEP state produces 0 units with minimal standby power (0.2-0.5 kW)."""
    sim = FactorySimulator(seed=42)
    sim.set_machine_state("M01", MachineState.SLEEP)

    batch = [sim.step(dt_seconds=1.0)[0] for _ in range(30)]
    for r in batch:
        assert r.production_delta == 0
        assert r.machine_state == MachineState.SLEEP
        assert 0.20 <= r.power_kw <= 0.50, f"Sleep power out of range: {r.power_kw}"
        assert r.rpm == 0.0
        assert r.vibration is not None and r.vibration < 0.03


def test_degraded_behavior_relationships():
    """Verify DEGRADED state causes higher power, higher vibration, higher temp, lower health."""
    sim = FactorySimulator(seed=42)

    # 1. Baseline normal run on M03 (rated 8.2 kW)
    sim.set_machine_state("M03", MachineState.RUNNING)
    normal_recs = [sim.step(dt_seconds=1.0)[2] for _ in range(20)]
    avg_norm_p = sum(r.power_kw for r in normal_recs) / len(normal_recs)
    avg_norm_vib = sum(r.vibration for r in normal_recs) / len(normal_recs)
    norm_health = normal_recs[-1].health_score

    # 2. Trigger degradation
    sim.trigger_degradation("M03", level_increment=0.50)
    deg_recs = [sim.step(dt_seconds=1.0)[2] for _ in range(40)]
    avg_deg_p = sum(r.power_kw for r in deg_recs) / len(deg_recs)
    avg_deg_vib = sum(r.vibration for r in deg_recs) / len(deg_recs)
    deg_health = deg_recs[-1].health_score
    deg_anomaly = deg_recs[-1].anomaly_score

    assert avg_deg_p > avg_norm_p, "Degraded power did not increase!"
    assert avg_deg_vib > avg_norm_vib * 1.5, "Degraded vibration did not increase!"
    assert deg_health < norm_health, "Degraded health did not decrease!"
    assert deg_anomaly > 0.35, f"Anomaly score did not elevate: {deg_anomaly}"


def test_overload_behavior():
    """Verify OVERLOAD state causes elevated current, power, and temperature."""
    sim = FactorySimulator(seed=42)
    sim.trigger_overload("M02")

    records = [sim.step(dt_seconds=1.0)[1] for _ in range(25)]
    m02_profile = DEFAULT_PROFILES["M02"]

    avg_p = sum(r.power_kw for r in records) / len(records)
    assert avg_p > m02_profile.rated_power_kw * 1.25, f"Overload power too low: {avg_p}"
    assert records[-1].current_a is not None and records[-1].current_a > 15.0
    assert records[-1].anomaly_score > 0.30


def test_recovery_behavior():
    """Verify that after triggering recovery, health trends upward and degradation dissipates."""
    sim = FactorySimulator(seed=42)
    # Degrade machine
    sim.trigger_degradation("M03", level_increment=0.60)
    deg_recs = [sim.step(dt_seconds=1.0)[2] for _ in range(20)]
    lowest_health = deg_recs[-1].health_score

    # Trigger recovery & run for recovery period
    sim.trigger_recovery("M03")
    recov_recs = [sim.step(dt_seconds=1.0)[2] for _ in range(40)]
    final_health = recov_recs[-1].health_score
    final_anomaly = recov_recs[-1].anomaly_score

    assert final_health > lowest_health, f"Health did not recover: {lowest_health} -> {final_health}"
    assert final_anomaly < deg_recs[-1].anomaly_score


# ==============================================================================
# 4. DETERMINISM & REPRODUCIBILITY
# ==============================================================================

def test_deterministic_seed_reproducibility():
    """Verify identical seeds produce identical telemetry sequences."""
    sim1 = FactorySimulator(seed=12345)
    sim2 = FactorySimulator(seed=12345)

    for _ in range(15):
        recs1 = sim1.step(dt_seconds=1.0)
        recs2 = sim2.step(dt_seconds=1.0)
        for r1, r2 in zip(recs1, recs2):
            assert r1.machine_id == r2.machine_id
            assert r1.power_kw == r2.power_kw
            assert r1.energy_kwh == r2.energy_kwh
            assert r1.temperature_c == r2.temperature_c
            assert r1.vibration == r2.vibration
            assert r1.health_score == r2.health_score


# ==============================================================================
# 5. STATE TRANSITIONS & DATA GENERATION (100 STEPS / 400 RECORDS)
# ==============================================================================

def test_state_transitions():
    """Verify state transitions: RUNNING -> IDLE -> SLEEP -> RUNNING."""
    sim = FactorySimulator(seed=42)
    m01 = sim.get_machine("M01")

    assert m01.state == MachineState.RUNNING
    sim.set_machine_state("M01", MachineState.IDLE)
    assert m01.state == MachineState.IDLE
    sim.set_machine_state("M01", MachineState.SLEEP)
    assert m01.state == MachineState.SLEEP
    sim.set_machine_state("M01", MachineState.RUNNING)
    assert m01.state == MachineState.RUNNING


def test_large_dataset_generation_quality():
    """
    Generate 100 simulation steps across 4 machines (400 total records).
    Verify all 400 strictly validate, have no negative metrics, and bounded scores.
    """
    sim = FactorySimulator(seed=999)
    all_records = []
    for _ in range(100):
        step_recs = sim.step(dt_seconds=1.0)
        all_records.extend(step_recs)

    assert len(all_records) == 400
    for r in all_records:
        assert isinstance(r, TelemetryRecord)
        assert r.power_kw >= 0.0
        assert r.energy_kwh >= 0.0
        assert r.production_count is not None and r.production_count >= 0
        assert r.health_score is not None and 0.0 <= r.health_score <= 100.0
        assert r.anomaly_score is not None and 0.0 <= r.anomaly_score <= 1.0


# ==============================================================================
# 6. DEMO SCENARIO SEQUENCE
# ==============================================================================

def test_demo_scenario_controller():
    """Verify DemoScenarioController executes all 6 phases successfully."""
    sim = FactorySimulator(seed=42)
    controller = DemoScenarioController(sim)
    demo_results = controller.run_full_demo(steps_per_phase=5, dt_seconds=1.0)

    expected_phases = [
        "PHASE_A_NORMAL",
        "PHASE_B_IDLE",
        "PHASE_C_SLEEP",
        "PHASE_D_DEGRADED",
        "PHASE_E_OVERLOAD",
        "PHASE_F_RECOVERY",
    ]
    assert list(demo_results.keys()) == expected_phases
    for phase_name in expected_phases:
        records = demo_results[phase_name]["records"]
        assert len(records) == 5  # 5 steps per phase
        assert len(records[0]) == 4  # 4 machines per step
