"""
Specific Energy Consumption (SEC) and Energy Per Unit Analytics.
Core industrial KPI: SEC = Energy Consumed (kWh) / Production (units).
Provides safe division, zero-production handling, and mathematical transparency.
"""

from typing import Optional


def calculate_sec(energy_kwh: Optional[float], production_units: Optional[float]) -> Optional[float]:
    """
    Calculates Specific Energy Consumption (SEC) in kWh/unit.

    Rules:
    - If production_units is None, <= 0, or energy_kwh is None or < 0: returns None (never divides by zero).
    - Preserves deterministic rounding to 4 decimal places.
    """
    if energy_kwh is None or production_units is None:
        return None
    if production_units <= 0 or energy_kwh < 0:
        return None
    return round(energy_kwh / production_units, 4)


def calculate_energy_per_unit(energy_kwh: Optional[float], production_units: Optional[float]) -> Optional[float]:
    """
    Calculates Energy Per Unit in kWh/unit.
    Numerically equivalent to SEC; shares common implementation.
    """
    return calculate_sec(energy_kwh=energy_kwh, production_units=production_units)
