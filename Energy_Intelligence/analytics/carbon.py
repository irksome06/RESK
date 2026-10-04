"""
Industrial Carbon Emissions and Electricity Economics Analytics.
Translates electrical energy consumption into CO2 emissions and utility costs
tailored for Indian SME smart manufacturing contexts.
"""

from typing import Optional
from simulator.config import settings


def calculate_co2_emissions(
    energy_kwh: Optional[float],
    emission_factor: Optional[float] = None,
) -> Optional[float]:
    """
    Calculates carbon footprint equivalent in kg CO2.
    Formula: CO2 (kg) = Energy (kWh) × Grid Emission Factor (kg CO2 / kWh).
    Default emission factor: CEA India Baseline (~0.716 kg CO2/kWh).
    """
    if energy_kwh is None or energy_kwh < 0:
        return None
    factor = emission_factor if emission_factor is not None else settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH
    return round(energy_kwh * factor, 4)


def calculate_energy_cost(
    energy_kwh: Optional[float],
    tariff_inr: Optional[float] = None,
) -> Optional[float]:
    """
    Calculates deterministic electricity cost in INR (₹).
    Formula: Cost (₹) = Energy (kWh) × Tariff (₹/kWh).
    Default tariff: Commercial/Industrial LT tariff (~₹8.50/kWh).
    """
    if energy_kwh is None or energy_kwh < 0:
        return None
    rate = tariff_inr if tariff_inr is not None else settings.ELECTRICITY_TARIFF_INR_PER_KWH
    return round(energy_kwh * rate, 2)
