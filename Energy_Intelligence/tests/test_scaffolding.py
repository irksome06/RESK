"""
Phase 1 Scaffolding & Architecture Verification Tests.
Verifies structure, module importability, config resolution, and initial endpoints.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure person3_energy_intelligence is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from simulator.config import settings
from api.main import app
from analytics.sec import calculate_sec
from analytics.carbon import calculate_co2_emissions
from analytics.savings import calculate_savings


client = TestClient(app)


def test_directory_structure_exists():
    """Verify core Phase 1 directories exist."""
    required_dirs = [
        "simulator",
        "mqtt",
        "api",
        "database",
        "analytics",
        "ml",
        "llm",
        "data/raw",
        "data/processed",
        "tests",
    ]
    for d in required_dirs:
        dir_path = BASE_DIR / d
        assert dir_path.exists(), f"Missing required directory: {d}"
        assert dir_path.is_dir(), f"Path is not a directory: {d}"


def test_configuration_defaults():
    """Verify settings load valid defaults."""
    assert settings.API_PORT == 8000
    assert settings.ELECTRICITY_TARIFF_INR_PER_KWH > 0
    assert settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH > 0
    assert settings.MQTT_BROKER_PORT == 1883


def test_fastapi_health_endpoint():
    """Verify that the FastAPI service boots and health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] in ("connected", "unavailable")


def test_fastapi_root_endpoint():
    """Verify root endpoint responds with engine metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "Energy & Production Intelligence Engine"
    assert data["status"] == "online"


def test_basic_analytics_functions():
    """Verify baseline analytical calculations work deterministically."""
    # 10 kWh for 100 units -> 0.1 kWh/unit
    sec = calculate_sec(energy_kwh=10.0, production_units=100)
    assert sec == 0.1

    # Zero production protection -> returns None
    assert calculate_sec(energy_kwh=10.0, production_units=0) is None

    # Carbon emissions: 10 kWh * 0.716 kg/kWh = 7.16 kg CO2
    co2 = calculate_co2_emissions(energy_kwh=10.0, emission_factor=0.716)
    assert co2 == 7.16

    # Savings calculation: baseline 20 kWh, actual 15 kWh (5 kWh saved)
    savings = calculate_savings(baseline_kwh=20.0, actual_kwh=15.0, tariff_inr=8.50, emission_factor_kg=0.716)
    assert savings["energy_saved_kwh"] == 5.0
    assert savings["cost_saved_inr"] == 42.50
    assert savings["percentage_reduction"] == 25.0
