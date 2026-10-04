"""
Comprehensive Deterministic Unit & Integration Test Suite for Phase 7 Analytics.
Verifies all mathematical KPIs, data quality checks, edge cases, invariants,
and FastAPI analytics endpoints with manually verifiable deterministic datasets.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from database.schemas import TelemetryRecord, MachineState
from database.telemetry_repository import telemetry_repo
from analytics.sec import calculate_sec, calculate_energy_per_unit
from analytics.carbon import calculate_co2_emissions, calculate_energy_cost
from analytics.production import calculate_production_metrics
from analytics.utilization import calculate_utilization, calculate_state_durations
from analytics.energy import calculate_energy_consumption, calculate_state_energy_breakdown
from analytics.engine import analyze_machine, analyze_factory
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    telemetry_repo.clear_all()
    yield
    telemetry_repo.clear_all()


# ==============================================================================
# DETERMINISTIC TEST FIXTURES
# ==============================================================================

def make_deterministic_1hr_m01_records() -> list[TelemetryRecord]:
    """
    Creates exactly 1 hour of telemetry for M01:
    - 10:00 to 10:15: RUNNING  (8.0 kW, delta 2.0 kWh, +25 units)
    - 10:15 to 10:30: IDLE     (1.2 kW, delta 0.3 kWh, +0 units)
    - 10:30 to 10:45: SLEEP    (0.2 kW, delta 0.05 kWh, +0 units)
    - 10:45 to 11:00: DEGRADED (9.6 kW, delta 2.4 kWh, +15 units)

    Expected Totals:
    - Duration: 1.0 hour (3600 sec)
    - Total Energy: 4.75 kWh
    - Running Energy: 2.0 kWh, Idle: 0.3 kWh, Sleep: 0.05 kWh, Degraded: 2.4 kWh, Overload: 0.0 kWh
    - Total Production: 40 units
    - SEC: 4.75 / 40 = 0.1188 kWh/unit
    - Utilization: (15 min running + 15 min degraded) / 60 min = 50.0%
    """
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    return [
        TelemetryRecord(
            timestamp=t0,
            machine_id="M01",
            power_kw=8.0,
            energy_kwh=100.0,
            machine_state=MachineState.RUNNING,
            production_count=100,
            production_delta=0,
        ),
        TelemetryRecord(
            timestamp=t0 + timedelta(minutes=15),
            machine_id="M01",
            power_kw=8.0,
            energy_kwh=102.0,
            machine_state=MachineState.RUNNING,
            production_count=125,
            production_delta=25,
        ),
        TelemetryRecord(
            timestamp=t0 + timedelta(minutes=30),
            machine_id="M01",
            power_kw=1.2,
            energy_kwh=102.3,
            machine_state=MachineState.IDLE,
            production_count=125,
            production_delta=0,
        ),
        TelemetryRecord(
            timestamp=t0 + timedelta(minutes=45),
            machine_id="M01",
            power_kw=0.2,
            energy_kwh=102.35,
            machine_state=MachineState.SLEEP,
            production_count=125,
            production_delta=0,
        ),
        TelemetryRecord(
            timestamp=t0 + timedelta(minutes=60),
            machine_id="M01",
            power_kw=9.6,
            energy_kwh=104.75,
            machine_state=MachineState.DEGRADED,
            production_count=140,
            production_delta=15,
        ),
    ]


# ==============================================================================
# 1. CORE ENERGY & INTERVAL TESTS
# ==============================================================================

def test_energy_from_cumulative_meter():
    """Verify total energy is derived accurately from monotonic cumulative meter deltas."""
    records = make_deterministic_1hr_m01_records()
    energy, method, warnings = calculate_energy_consumption(records)
    assert method == "METER_DELTA"
    assert energy == 4.75
    assert len(warnings) == 0


def test_energy_interval_handling_irregular_timestamps():
    """Verify energy calculation works with irregular timestamp intervals (e.g. 5s, 42s, 113s)."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    records = [
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=6.0, energy_kwh=10.0, machine_state=MachineState.RUNNING),
        TelemetryRecord(timestamp=t0 + timedelta(seconds=7), machine_id="M01", power_kw=6.0, energy_kwh=10.0117, machine_state=MachineState.RUNNING),
        TelemetryRecord(timestamp=t0 + timedelta(seconds=49), machine_id="M01", power_kw=6.0, energy_kwh=10.0817, machine_state=MachineState.RUNNING),
        TelemetryRecord(timestamp=t0 + timedelta(seconds=180), machine_id="M01", power_kw=6.0, energy_kwh=10.3, machine_state=MachineState.RUNNING),
    ]
    energy, method, warnings = calculate_energy_consumption(records)
    assert method == "METER_DELTA"
    assert energy == 0.3


def test_energy_from_power_integration_fallback():
    """Verify trapezoidal power integration is used when cumulative energy register is None."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    # 3600 seconds at constant 10 kW = exactly 10.0 kWh
    records = [
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=10.0, energy_kwh=0.0, machine_state=MachineState.RUNNING),
        TelemetryRecord(timestamp=t0 + timedelta(seconds=3600), machine_id="M01", power_kw=10.0, energy_kwh=0.0, machine_state=MachineState.RUNNING),
    ]
    # Set energy_kwh to None
    records[0].energy_kwh = None  # type: ignore
    records[1].energy_kwh = None  # type: ignore

    energy, method, warnings = calculate_energy_consumption(records)
    assert method == "POWER_INTEGRATION"
    assert energy == 10.0
    assert any("integrated instantaneous active power" in w for w in warnings)


def test_non_monotonic_energy_counter_detection():
    """Verify non-monotonic energy meter triggers INVALID_NON_MONOTONIC_ENERGY and returns None."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    records = [
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=5.0, energy_kwh=100.0, machine_state=MachineState.RUNNING),
        TelemetryRecord(timestamp=t0 + timedelta(seconds=30), machine_id="M01", power_kw=5.0, energy_kwh=95.0, machine_state=MachineState.RUNNING),  # Reset/drop
    ]
    energy, method, warnings = calculate_energy_consumption(records)
    assert energy is None
    assert method == "INVALID_NON_MONOTONIC_ENERGY"
    assert any("Non-monotonic" in w for w in warnings)


# ==============================================================================
# 2. PRODUCTION & RATE TESTS
# ==============================================================================

def test_production_from_cumulative_counter():
    """Verify production is derived correctly from last_count - first_count."""
    records = make_deterministic_1hr_m01_records()
    total_prod, rate, warnings = calculate_production_metrics(records, elapsed_hours=1.0)
    assert total_prod == 40  # 140 - 100
    assert rate == 40.0
    assert len(warnings) == 0


def test_production_from_production_delta_fallback():
    """Verify summing production_delta when cumulative production_count is None."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    records = [
        TelemetryRecord(timestamp=t0, machine_id="M04", power_kw=4.0, energy_kwh=10.0, machine_state=MachineState.RUNNING, production_count=None, production_delta=None),
        TelemetryRecord(timestamp=t0 + timedelta(minutes=15), machine_id="M04", power_kw=4.0, energy_kwh=11.0, machine_state=MachineState.RUNNING, production_count=None, production_delta=10),
        TelemetryRecord(timestamp=t0 + timedelta(minutes=30), machine_id="M04", power_kw=4.0, energy_kwh=12.0, machine_state=MachineState.RUNNING, production_count=None, production_delta=15),
    ]
    total_prod, rate, warnings = calculate_production_metrics(records, elapsed_hours=0.5)
    assert total_prod == 25
    assert rate == 50.0  # 25 units / 0.5 hours = 50.0 units/hr


def test_production_counter_reset_detection():
    """Verify counter reset (last < first) is flagged without returning negative production."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    records = [
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=5.0, energy_kwh=10.0, machine_state=MachineState.RUNNING, production_count=500, production_delta=0),
        TelemetryRecord(timestamp=t0 + timedelta(minutes=10), machine_id="M01", power_kw=5.0, energy_kwh=11.0, machine_state=MachineState.RUNNING, production_count=50, production_delta=50),
    ]
    total_prod, rate, warnings = calculate_production_metrics(records, elapsed_hours=10/60)
    assert any("PRODUCTION_COUNTER_RESET" in w for w in warnings)
    assert total_prod == 50  # Fallback to delta


def test_missing_production_handled_safely():
    """Verify machines with no production tracking return None rather than 0."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    records = [
        TelemetryRecord(timestamp=t0, machine_id="M04", power_kw=4.0, energy_kwh=10.0, machine_state=MachineState.RUNNING, production_count=None, production_delta=None),
        TelemetryRecord(timestamp=t0 + timedelta(minutes=10), machine_id="M04", power_kw=4.0, energy_kwh=11.0, machine_state=MachineState.RUNNING, production_count=None, production_delta=None),
    ]
    total_prod, rate, warnings = calculate_production_metrics(records, elapsed_hours=10/60)
    assert total_prod is None
    assert rate is None
    assert "PRODUCTION_UNAVAILABLE" in warnings


# ==============================================================================
# 3. SEC & ENERGY PER UNIT TESTS
# ==============================================================================

def test_specific_energy_consumption_calculation():
    """Verify SEC calculation: 4.75 kWh / 40 units = 0.1187 kWh/unit."""
    sec = calculate_sec(energy_kwh=4.75, production_units=40)
    assert sec == 0.1187

    # Energy per unit alias
    epu = calculate_energy_per_unit(energy_kwh=4.75, production_units=40)
    assert epu == 0.1187


def test_zero_production_sec_protection():
    """Verify zero production returns None rather than division by zero error or infinity."""
    assert calculate_sec(energy_kwh=10.0, production_units=0) is None
    assert calculate_sec(energy_kwh=10.0, production_units=-5) is None
    assert calculate_sec(energy_kwh=None, production_units=100) is None
    assert calculate_sec(energy_kwh=10.0, production_units=None) is None


# ==============================================================================
# 4. UTILIZATION & STATE BREAKDOWN TESTS
# ==============================================================================

def test_utilization_calculation():
    """Verify utilization calculation: 30 minutes productive out of 60 minutes = 50.0%."""
    records = make_deterministic_1hr_m01_records()
    durations, total_h, prod_h = calculate_state_durations(records)
    assert total_h == 1.0
    assert prod_h == 0.5  # 15m running + 15m degraded
    assert calculate_utilization(productive_time_sec=prod_h * 3600, total_observed_time_sec=total_h * 3600) == 50.0


def test_state_energy_breakdown():
    """Verify granular energy and time distribution across operational states."""
    records = make_deterministic_1hr_m01_records()
    breakdown = calculate_state_energy_breakdown(records, total_energy_kwh=4.75)

    assert breakdown.running == 2.0
    assert breakdown.idle == 0.3
    assert breakdown.sleep == 0.05
    assert breakdown.degraded == 2.4
    assert breakdown.overload == 0.0

    assert breakdown.idle_time_hours == 0.25
    assert breakdown.idle_power_average_kw == 1.2
    assert breakdown.idle_energy_pct == round((0.3 / 4.75) * 100.0, 2)
    assert breakdown.sleep_energy_pct == round((0.05 / 4.75) * 100.0, 2)


def test_overload_energy_tracking():
    """Verify OVERLOAD state correctly tracks energy and duration."""
    t0 = datetime(2026, 10, 2, 8, 0, 0, tzinfo=timezone.utc)
    records = [
        TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=15.0, energy_kwh=10.0, machine_state=MachineState.OVERLOAD),
        TelemetryRecord(timestamp=t0 + timedelta(minutes=10), machine_id="M01", power_kw=15.0, energy_kwh=12.5, machine_state=MachineState.OVERLOAD),
    ]
    breakdown = calculate_state_energy_breakdown(records, total_energy_kwh=2.5)
    assert breakdown.overload == 2.5
    assert breakdown.overload_time_hours == round(10 / 60, 4)


# ==============================================================================
# 5. COSTS & CO2 TESTS
# ==============================================================================

def test_electricity_cost_calculation():
    """Verify energy cost: 4.75 kWh * 8.50 INR/kWh = 40.38 INR."""
    cost = calculate_energy_cost(energy_kwh=4.75, tariff_inr=8.50)
    assert cost == 40.38
    assert calculate_energy_cost(energy_kwh=None) is None


def test_co2_emissions_calculation():
    """Verify CO2 emissions: 4.75 kWh * 0.716 kg CO2/kWh = 3.401 kg CO2."""
    co2 = calculate_co2_emissions(energy_kwh=4.75, emission_factor=0.716)
    assert co2 == 3.401
    assert calculate_co2_emissions(energy_kwh=None) is None


# ==============================================================================
# 6. MACHINE & FACTORY AGGREGATION TESTS
# ==============================================================================

def test_analyze_machine_full_workflow():
    """Verify analyze_machine computes and packages all KPIs into structured MachineEnergyAnalysis."""
    records = make_deterministic_1hr_m01_records()
    t_start = records[0].timestamp
    t_end = records[-1].timestamp

    analysis = analyze_machine(
        machine_id="M01",
        start_time=t_start,
        end_time=t_end,
        records=records,
    )

    assert analysis.machine_id == "M01"
    assert analysis.elapsed_hours == 1.0
    assert analysis.energy_kwh == 4.75
    assert analysis.production_units == 40
    assert analysis.production_rate_units_per_hour == 40.0
    assert analysis.sec_kwh_per_unit == 0.1187
    assert analysis.utilization_pct == 50.0
    assert analysis.state_energy.running == 2.0
    assert analysis.state_energy.idle == 0.3
    assert analysis.state_energy.sleep == 0.05
    assert analysis.state_energy.degraded == 2.4
    assert analysis.energy_cost_inr == 40.38
    assert analysis.co2_kg == 3.401
    assert analysis.data_quality.status == "OK"


def test_factory_aggregation_sec_uses_total_energy_over_total_production():
    """
    CRITICAL TEST: Verify factory SEC = Total Energy / Total Production,
    NEVER the naive average of machine SEC values.

    Setup:
    Machine A: 10 kWh, 100 units -> SEC = 0.10 kWh/unit
    Machine B: 90 kWh, 100 units -> SEC = 0.90 kWh/unit
    Naive average of SECs = (0.10 + 0.90) / 2 = 0.50 kWh/unit (WRONG!)
    Correct factory SEC = (10 + 90) / (100 + 100) = 100 / 200 = 0.50 kWh/unit.

    Now with unequal production weights:
    Machine A: 10 kWh, 100 units -> SEC = 0.10 kWh/unit
    Machine B: 90 kWh, 900 units -> SEC = 0.10 kWh/unit -> Factory SEC = 100 / 1000 = 0.10

    Unequal SEC and weights:
    Machine A: 20 kWh, 100 units (SEC = 0.20)
    Machine B: 80 kWh, 200 units (SEC = 0.40)
    Naive avg = (0.20 + 0.40) / 2 = 0.30
    Correct factory SEC = 100 kWh / 300 units = 0.3333 kWh/unit!
    """
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)

    # Machine A (M01): 20 kWh, 100 units
    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=20.0, energy_kwh=100.0, machine_state=MachineState.RUNNING, production_count=0))
    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t1, machine_id="M01", power_kw=20.0, energy_kwh=120.0, machine_state=MachineState.RUNNING, production_count=100))

    # Machine B (M02): 80 kWh, 200 units
    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t0, machine_id="M02", power_kw=80.0, energy_kwh=200.0, machine_state=MachineState.RUNNING, production_count=0))
    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t1, machine_id="M02", power_kw=80.0, energy_kwh=280.0, machine_state=MachineState.RUNNING, production_count=200))

    factory_analysis = analyze_factory(start_time=t0, end_time=t1)

    assert factory_analysis.total_factory_energy_kwh == 100.0
    assert factory_analysis.total_factory_production_units == 300
    # Must be 100 / 300 = 0.3333, NOT 0.30
    assert factory_analysis.factory_sec_kwh_per_unit == 0.3333


def test_property_state_energy_sum_equals_total_energy():
    """Invariant test: running + idle + sleep + degraded + overload == total_energy."""
    records = make_deterministic_1hr_m01_records()
    analysis = analyze_machine("M01", records[0].timestamp, records[-1].timestamp, records=records)
    se = analysis.state_energy
    sum_states = se.running + se.idle + se.sleep + se.degraded + se.overload
    assert abs(sum_states - analysis.energy_kwh) < 1e-4


# ==============================================================================
# 7. EDGE CASES & DATA QUALITY CHECKS
# ==============================================================================

def test_invalid_time_range():
    """Verify start_time >= end_time returns INVALID_TIME_RANGE."""
    t0 = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    analysis = analyze_machine("M01", start_time=t0, end_time=t0)
    assert analysis.data_quality.status == "INVALID_TIME_RANGE"
    assert analysis.elapsed_hours == 0.0


def test_empty_dataset_insufficient_data():
    """Verify empty query returns INSUFFICIENT_DATA status."""
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=2)
    analysis = analyze_machine("M01", start_time=t0, end_time=t1)
    assert analysis.data_quality.status == "INSUFFICIENT_DATA"
    assert analysis.energy_kwh is None


# ==============================================================================
# 8. FASTAPI REST ANALYTICS ENDPOINTS
# ==============================================================================

def test_fastapi_machine_analytics_endpoint():
    """Verify GET /analytics/machines/{machine_id} retrieves and calculates deterministic KPIs."""
    records = make_deterministic_1hr_m01_records()
    for r in records:
        telemetry_repo.save_telemetry(r)

    t_start = "2026-10-02T10:00:00Z"
    t_end = "2026-10-02T11:00:00Z"
    res = client.get(f"/analytics/machines/M01?start_time={t_start}&end_time={t_end}")
    assert res.status_code == 200
    data = res.json()
    assert data["machine_id"] == "M01"
    assert data["energy_kwh"] == 4.75
    assert data["production_units"] == 40
    assert data["sec_kwh_per_unit"] == 0.1187
    assert data["utilization_pct"] == 50.0
    assert data["state_energy"]["running"] == 2.0
    assert data["state_energy"]["idle"] == 0.3
    assert data["data_quality"]["status"] == "OK"


def test_fastapi_factory_analytics_endpoint():
    """Verify GET /analytics/factory calculates aggregate factory metrics across multiple machines."""
    records = make_deterministic_1hr_m01_records()
    for r in records:
        telemetry_repo.save_telemetry(r)

    t_start = "2026-10-02T10:00:00Z"
    t_end = "2026-10-02T11:00:00Z"
    res = client.get(f"/analytics/factory?start_time={t_start}&end_time={t_end}")
    assert res.status_code == 200
    data = res.json()
    assert data["machines_analyzed_count"] >= 1
    assert data["total_factory_energy_kwh"] == 4.75
    assert data["total_factory_production_units"] == 40
    assert data["factory_sec_kwh_per_unit"] == 0.1187


# ==============================================================================
# 9. PROPERTY & INVARIANT TESTS
# ==============================================================================

def test_invariants_properties():
    """Verify core invariants hold: energy >= 0, production >= 0, SEC >= 0."""
    records = make_deterministic_1hr_m01_records()
    analysis = analyze_machine("M01", records[0].timestamp, records[-1].timestamp, records=records)

    assert analysis.data_quality.status == "OK"
    assert analysis.energy_kwh >= 0
    assert analysis.production_units >= 0
    assert analysis.sec_kwh_per_unit >= 0
    assert 0.0 <= analysis.utilization_pct <= 100.0


def test_factory_energy_equals_sum_of_machine_energies():
    """Verify factory energy invariant: factory_energy == sum(machine_energies)."""
    t0 = datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)

    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t0, machine_id="M01", power_kw=10.0, energy_kwh=10.0, machine_state=MachineState.RUNNING))
    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t1, machine_id="M01", power_kw=10.0, energy_kwh=20.0, machine_state=MachineState.RUNNING))

    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t0, machine_id="M02", power_kw=5.0, energy_kwh=50.0, machine_state=MachineState.RUNNING))
    telemetry_repo.save_telemetry(TelemetryRecord(timestamp=t1, machine_id="M02", power_kw=5.0, energy_kwh=55.0, machine_state=MachineState.RUNNING))

    factory_analysis = analyze_factory(start_time=t0, end_time=t1)
    m1_analysis = analyze_machine("M01", start_time=t0, end_time=t1)
    m2_analysis = analyze_machine("M02", start_time=t0, end_time=t1)

    assert m1_analysis.energy_kwh == 10.0
    assert m2_analysis.energy_kwh == 5.0
    assert factory_analysis.total_factory_energy_kwh == m1_analysis.energy_kwh + m2_analysis.energy_kwh

