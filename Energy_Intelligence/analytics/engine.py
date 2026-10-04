"""
Deterministic Energy & Production Analytics Engine.
Orchestrates machine-level and factory-level deterministic aggregations.
Implements mathematically sound factory aggregation rules:
- Factory SEC = Total Energy / Total Production (never average of SECs).
- Factory Utilization = Total Productive Hours / Total Observed Hours.
"""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from database.database import get_db_context
from database.schemas import (
    TelemetryRecord,
    MachineEnergyAnalysis,
    FactoryEnergyAnalysis,
    StateEnergyBreakdown,
    DataQualityReport,
)
from database.telemetry_repository import telemetry_repo
from simulator.config import settings
from simulator.machine_simulator import DEFAULT_PROFILES
from analytics.energy import calculate_energy_consumption, calculate_state_energy_breakdown
from analytics.production import calculate_production_metrics
from analytics.sec import calculate_sec
from analytics.utilization import calculate_utilization, calculate_state_durations
from analytics.carbon import calculate_co2_emissions, calculate_energy_cost


def analyze_machine(
    machine_id: str,
    start_time: datetime,
    end_time: datetime,
    electricity_rate_inr_per_kwh: Optional[float] = None,
    grid_emission_factor_kg_per_kwh: Optional[float] = None,
    records: Optional[List[TelemetryRecord]] = None,
    db: Optional[Session] = None,
) -> MachineEnergyAnalysis:
    """
    Computes complete deterministic energy and production metrics for a single machine over a time window.
    """
    # Normalize timestamps to UTC
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    else:
        start_time = start_time.astimezone(timezone.utc)

    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    else:
        end_time = end_time.astimezone(timezone.utc)

    tariff = electricity_rate_inr_per_kwh or settings.ELECTRICITY_TARIFF_INR_PER_KWH
    factor = grid_emission_factor_kg_per_kwh or settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH

    # Validate time range
    if start_time >= end_time:
        return MachineEnergyAnalysis(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time,
            elapsed_hours=0.0,
            electricity_rate_inr_per_kwh=tariff,
            grid_emission_factor_kg_per_kwh=factor,
            data_quality=DataQualityReport(
                status="INVALID_TIME_RANGE",
                warnings=["start_time must be strictly earlier than end_time"],
            ),
        )

    # Fetch telemetry if not directly injected
    if records is None:
        records = telemetry_repo.get_telemetry_window(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time,
            db=db,
        )

    # Check for empty / insufficient data
    if len(records) < 2:
        nominal_hours = round((end_time - start_time).total_seconds() / 3600.0, 4)
        return MachineEnergyAnalysis(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time,
            elapsed_hours=nominal_hours,
            electricity_rate_inr_per_kwh=tariff,
            grid_emission_factor_kg_per_kwh=factor,
            data_quality=DataQualityReport(
                status="INSUFFICIENT_DATA",
                warnings=["At least two telemetry records are required in the time window"],
            ),
        )

    # Compute actual elapsed duration
    actual_elapsed_hours = round(
        (records[-1].timestamp - records[0].timestamp).total_seconds() / 3600.0, 4
    )

    # 1. Energy
    energy_kwh, calc_method, energy_warnings = calculate_energy_consumption(records)

    # 2. State Breakdown
    state_energy = calculate_state_energy_breakdown(records, total_energy_kwh=energy_kwh)

    # 3. Production
    prod_units, prod_rate, prod_warnings = calculate_production_metrics(
        records, elapsed_hours=actual_elapsed_hours
    )

    # 4. SEC
    sec = calculate_sec(energy_kwh=energy_kwh, production_units=prod_units)

    # 5. Utilization
    durations, total_h, prod_h = calculate_state_durations(records)
    utilization = calculate_utilization(
        productive_time_sec=prod_h * 3600.0,
        total_observed_time_sec=total_h * 3600.0,
    )

    # 6. Cost & Emissions
    cost_inr = calculate_energy_cost(energy_kwh=energy_kwh, tariff_inr=tariff)
    co2_kg = calculate_co2_emissions(energy_kwh=energy_kwh, emission_factor=factor)

    # Data Quality status determination
    warnings = energy_warnings + prod_warnings
    if energy_kwh is None and "INVALID_NON_MONOTONIC_ENERGY" in str(energy_warnings):
        status = "INVALID_NON_MONOTONIC_ENERGY"
    elif "PRODUCTION_COUNTER_RESET" in warnings:
        status = "PRODUCTION_COUNTER_RESET"
    elif prod_units is None and "PRODUCTION_UNAVAILABLE" in warnings:
        status = "PRODUCTION_UNAVAILABLE"
    else:
        status = "OK"

    return MachineEnergyAnalysis(
        machine_id=machine_id,
        start_time=start_time,
        end_time=end_time,
        elapsed_hours=actual_elapsed_hours,
        energy_kwh=energy_kwh,
        production_units=prod_units,
        production_rate_units_per_hour=prod_rate,
        sec_kwh_per_unit=sec,
        utilization_pct=utilization,
        state_energy=state_energy,
        energy_cost_inr=cost_inr,
        electricity_rate_inr_per_kwh=tariff,
        co2_kg=co2_kg,
        grid_emission_factor_kg_per_kwh=factor,
        data_quality=DataQualityReport(
            status=status,
            calculation_method=calc_method,
            warnings=warnings,
        ),
    )


def analyze_factory(
    start_time: datetime,
    end_time: datetime,
    electricity_rate_inr_per_kwh: Optional[float] = None,
    grid_emission_factor_kg_per_kwh: Optional[float] = None,
    db: Optional[Session] = None,
) -> FactoryEnergyAnalysis:
    """
    Computes factory-wide deterministic aggregation across all known machines.
    Aggregates SEC correctly: factory_SEC = total_energy / total_production.
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    else:
        start_time = start_time.astimezone(timezone.utc)

    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    else:
        end_time = end_time.astimezone(timezone.utc)

    nominal_hours = round((end_time - start_time).total_seconds() / 3600.0, 4)

    if start_time >= end_time:
        return FactoryEnergyAnalysis(
            start_time=start_time,
            end_time=end_time,
            elapsed_hours=0.0,
            machines_analyzed_count=0,
            data_quality=DataQualityReport(
                status="INVALID_TIME_RANGE",
                warnings=["start_time must be strictly earlier than end_time"],
            ),
        )

    # Discover machines to analyze
    known_db_ids = telemetry_repo.get_known_machine_ids(db=db)
    all_machine_ids = sorted(list(set(DEFAULT_PROFILES.keys()) | set(known_db_ids)))

    machine_analyses: List[MachineEnergyAnalysis] = []
    for m_id in all_machine_ids:
        m_analysis = analyze_machine(
            machine_id=m_id,
            start_time=start_time,
            end_time=end_time,
            electricity_rate_inr_per_kwh=electricity_rate_inr_per_kwh,
            grid_emission_factor_kg_per_kwh=grid_emission_factor_kg_per_kwh,
            db=db,
        )
        # Only include machines that have data or were observed
        if m_analysis.data_quality.status != "INSUFFICIENT_DATA":
            machine_analyses.append(m_analysis)

    if not machine_analyses:
        return FactoryEnergyAnalysis(
            start_time=start_time,
            end_time=end_time,
            elapsed_hours=nominal_hours,
            machines_analyzed_count=0,
            data_quality=DataQualityReport(
                status="INSUFFICIENT_DATA",
                warnings=["No machines had sufficient telemetry within the requested time range"],
            ),
        )

    # 1. Total Energy
    valid_energies = [m.energy_kwh for m in machine_analyses if m.energy_kwh is not None]
    total_factory_energy = round(sum(valid_energies), 4) if valid_energies else None

    # 2. Total Production
    valid_prods = [m.production_units for m in machine_analyses if m.production_units is not None]
    total_factory_prod = sum(valid_prods) if valid_prods else None

    # 3. Factory SEC: Total Factory Energy / Total Factory Production
    factory_sec = calculate_sec(energy_kwh=total_factory_energy, production_units=total_factory_prod)

    # 4. Factory Utilization: Sum of productive hours / Sum of total observed hours
    total_observed_hours = sum(m.elapsed_hours for m in machine_analyses)
    total_productive_hours = sum(
        (m.state_energy.running_time_hours + m.state_energy.degraded_time_hours + m.state_energy.overload_time_hours)
        for m in machine_analyses
    )
    factory_utilization = calculate_utilization(
        productive_time_sec=total_productive_hours * 3600.0,
        total_observed_time_sec=total_observed_hours * 3600.0,
    )

    # 5. Factory State Breakdown Sums
    factory_running_e = round(sum(m.state_energy.running for m in machine_analyses), 4)
    factory_idle_e = round(sum(m.state_energy.idle for m in machine_analyses), 4)
    factory_sleep_e = round(sum(m.state_energy.sleep for m in machine_analyses), 4)
    factory_degraded_e = round(sum(m.state_energy.degraded for m in machine_analyses), 4)
    factory_overload_e = round(sum(m.state_energy.overload for m in machine_analyses), 4)

    factory_idle_h = round(sum(m.state_energy.idle_time_hours for m in machine_analyses), 4)
    factory_sleep_h = round(sum(m.state_energy.sleep_time_hours for m in machine_analyses), 4)

    idle_avg_pwr = round(factory_idle_e / factory_idle_h, 3) if factory_idle_h > 0 else 0.0
    idle_pct = round((factory_idle_e / total_factory_energy) * 100.0, 2) if total_factory_energy and total_factory_energy > 0 else 0.0
    sleep_pct = round((factory_sleep_e / total_factory_energy) * 100.0, 2) if total_factory_energy and total_factory_energy > 0 else 0.0

    state_energy = StateEnergyBreakdown(
        running=factory_running_e,
        idle=factory_idle_e,
        sleep=factory_sleep_e,
        degraded=factory_degraded_e,
        overload=factory_overload_e,
        running_energy_kwh=factory_running_e,
        idle_energy_kwh=factory_idle_e,
        sleep_energy_kwh=factory_sleep_e,
        degraded_energy_kwh=factory_degraded_e,
        overload_energy_kwh=factory_overload_e,
        idle_time_hours=factory_idle_h,
        sleep_time_hours=factory_sleep_h,
        idle_power_average_kw=idle_avg_pwr,
        idle_energy_pct=idle_pct,
        sleep_energy_pct=sleep_pct,
    )

    # 6. Costs & CO2
    valid_costs = [m.energy_cost_inr for m in machine_analyses if m.energy_cost_inr is not None]
    total_cost = round(sum(valid_costs), 2) if valid_costs else None

    valid_co2 = [m.co2_kg for m in machine_analyses if m.co2_kg is not None]
    total_co2 = round(sum(valid_co2), 4) if valid_co2 else None

    warnings: List[str] = []
    for m in machine_analyses:
        for w in m.data_quality.warnings:
            if w not in warnings:
                warnings.append(f"[{m.machine_id}] {w}")

    return FactoryEnergyAnalysis(
        start_time=start_time,
        end_time=end_time,
        elapsed_hours=nominal_hours,
        machines_analyzed_count=len(machine_analyses),
        total_factory_energy_kwh=total_factory_energy,
        total_factory_production_units=total_factory_prod,
        factory_sec_kwh_per_unit=factory_sec,
        factory_utilization_pct=factory_utilization,
        state_energy=state_energy,
        total_energy_cost_inr=total_cost,
        total_co2_kg=total_co2,
        machines=machine_analyses,
        data_quality=DataQualityReport(
            status="OK" if not warnings else "OK_WITH_WARNINGS",
            warnings=warnings,
        ),
    )
