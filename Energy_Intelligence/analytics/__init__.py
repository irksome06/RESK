"""
Deterministic Energy & Production Analytics module for Person 3.
Provides mathematically transparent industrial KPIs:
- Specific Energy Consumption (SEC) & Energy per unit
- Production throughput and rates
- Productive machine utilization
- Granular operational state energy allocations (running, idle, sleep, degraded, overload)
- Deterministic utility costs and CO2 emissions
- Individual machine and factory-wide aggregations
"""

from analytics.sec import calculate_sec, calculate_energy_per_unit
from analytics.carbon import calculate_co2_emissions, calculate_energy_cost
from analytics.production import calculate_production_metrics
from analytics.utilization import calculate_utilization, calculate_state_durations, PRODUCTIVE_STATES, NON_PRODUCTIVE_STATES
from analytics.energy import calculate_energy_consumption, calculate_state_energy_breakdown
from analytics.engine import analyze_machine, analyze_factory

__all__ = [
    "calculate_sec",
    "calculate_energy_per_unit",
    "calculate_co2_emissions",
    "calculate_energy_cost",
    "calculate_production_metrics",
    "calculate_utilization",
    "calculate_state_durations",
    "calculate_energy_consumption",
    "calculate_state_energy_breakdown",
    "analyze_machine",
    "analyze_factory",
    "PRODUCTIVE_STATES",
    "NON_PRODUCTIVE_STATES",
]
