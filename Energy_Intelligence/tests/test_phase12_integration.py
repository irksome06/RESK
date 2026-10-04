"""
Phase 12 End-to-End Integration & Demonstration Test Suite.
Validates the complete Smart Manufacturing pipeline:
1. Unified Demo Status Endpoint (GET /demo/status)
2. Unified Factory Snapshot Endpoint (GET /demo/factory)
3. Unified Machine Detail Endpoint (GET /demo/machine/{id})
4. Simulator -> MQTT -> Ingestion Pipeline Flow
5. Persistent Database Storage
6. Deterministic Analytics Engine Availability
7. Multi-Step Short-Horizon Energy Forecasting
8. Savings Estimation & Verification Availability
9. Optimization Opportunity Intelligence
10. Energy Copilot Integration & Fallback Handling
11. Dashboard API Contract Compatibility
12. Deterministic Scenario Controller & Reproducibility
"""

import os
import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from api.main import app
from database.schemas import TelemetryRecord, MachineState
from database.telemetry_repository import telemetry_repo
from api.telemetry_store import telemetry_store, ingest_telemetry_record
from simulator.machine_simulator import FactorySimulator, DEFAULT_PROFILES
from simulator.scenarios import DemoScenarioController, ScenarioPhase
from simulator.demo_state import demo_state
from mqtt.subscriber import MQTTSubscriber
from mqtt.topics import build_telemetry_topic
from scripts.run_factory_demo import run_pipeline_demo, MockMQTTMessage


@pytest.fixture(scope="module")
def client():
    """TestClient fixture for FastAPI application."""
    return TestClient(app)


def test_demo_status_endpoint(client):
    """1. Test GET /demo/status returns valid schema and system health signals."""
    response = client.get("/demo/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("IDLE", "RUNNING", "COMPLETED")
    assert "running" in data
    assert "elapsed_time_seconds" in data
    assert "telemetry_count" in data
    assert data["machines_active"] == 4
    assert "current_scenario_phase" in data
    assert "database_connected" in data
    assert "mqtt_connected" in data
    assert "demo_mode" in data


def test_demo_factory_endpoint(client):
    """2. Test GET /demo/factory returns comprehensive unified snapshot."""
    response = client.get("/demo/factory")
    assert response.status_code == 200
    data = response.json()

    assert "timestamp" in data
    assert "machines" in data
    assert set(data["machines"]) == {"M01", "M02", "M03", "M04"}

    # Production section
    assert "production" in data
    assert "total_units" in data["production"]
    assert "active_producing_machines" in data["production"]

    # Energy section
    assert "energy" in data
    assert "actual_energy_kwh" in data["energy"]
    assert "expected_energy_kwh" in data["energy"]
    assert "total_power_kw" in data["energy"]
    assert "cost_inr" in data["energy"]
    assert "co2_kg" in data["energy"]

    # SEC and utilization
    assert "utilization" in data
    assert 0.0 <= data["utilization"] <= 1.0

    # Baseline & Deviation
    assert "baseline" in data
    assert "deviation" in data
    assert data["deviation"]["status"] in ("NORMAL", "ELEVATED", "HIGH")

    # Forecast
    assert "forecast" in data
    assert data["forecast"]["horizon_minutes"] == 5
    assert "total_forecast_kwh" in data["forecast"]

    # Savings & Efficiency
    assert "savings" in data
    assert "potential_savings_kwh" in data["savings"]
    assert "potential_savings_inr" in data["savings"]
    assert "potential_co2_kg" in data["savings"]
    assert "efficiency" in data

    # Machine status list
    assert "machine_status" in data
    assert len(data["machine_status"]) == 4
    for m in data["machine_status"]:
        assert "machine_id" in m
        assert "state" in m
        assert "power_kw" in m
        assert "energy_kwh" in m


def test_demo_machine_endpoint(client):
    """3. Test GET /demo/machine/{machine_id} for valid and invalid machine IDs."""
    # Test valid machine M03
    res_m03 = client.get("/demo/machine/M03")
    assert res_m03.status_code == 200
    m03_data = res_m03.json()
    assert m03_data["machine_id"] == "M03"
    assert "machine_name" in m03_data
    assert "current_state" in m03_data
    assert "power_kw" in m03_data
    assert "energy_kwh" in m03_data
    assert "health_context" in m03_data
    assert "health_score" in m03_data["health_context"]
    assert "temperature_c" in m03_data["health_context"]
    assert "optimization_opportunities" in m03_data

    # Test valid machine M01
    res_m01 = client.get("/demo/machine/M01")
    assert res_m01.status_code == 200
    assert res_m01.json()["machine_id"] == "M01"

    # Test 404 for unknown machine
    res_invalid = client.get("/demo/machine/INVALID_MACHINE_99")
    assert res_invalid.status_code == 404


def test_simulator_mqtt_ingestion_flow():
    """4. Test physical simulator -> MQTT serialization -> subscriber parsing -> store ingestion."""
    sim = FactorySimulator(seed=101)
    records = sim.step(dt_seconds=1.0)
    assert len(records) == 4

    ingested_records = []
    subscriber = MQTTSubscriber(
        client_id="test_flow_sub",
        on_telemetry=lambda r: ingested_records.append(r),
    )

    # Serialize to JSON and deliver via subscriber message handler
    for r in records:
        topic = build_telemetry_topic(r.machine_id)
        payload = r.model_dump_json().encode("utf-8")
        msg = MockMQTTMessage(topic=topic, payload=payload)
        subscriber._on_message(None, None, msg)

    assert len(ingested_records) == 4
    for orig, ingested in zip(records, ingested_records):
        assert orig.machine_id == ingested.machine_id
        assert round(orig.power_kw, 2) == round(ingested.power_kw, 2)
        assert orig.machine_state == ingested.machine_state


def test_persistence_integrity():
    """5. Test that ingested records are stored in the database repository."""
    from datetime import timedelta
    test_rec = TelemetryRecord(
        timestamp=datetime.now(timezone.utc) + timedelta(hours=1),
        machine_id="M01",
        power_kw=14.5,
        energy_kwh=102.34,
        machine_state=MachineState.RUNNING,
        production_count=50,
        production_delta=1,
    )
    ingest_telemetry_record(test_rec)

    # Check store and repo
    latest_store = telemetry_store.get_latest("M01")
    assert latest_store is not None
    assert latest_store.power_kw == 14.5

    recent_db = telemetry_repo.get_recent_telemetry(limit=5, machine_id="M01")
    assert len(recent_db) >= 1


def test_analytics_availability(client):
    """6. Test deterministic analytics endpoint availability."""
    start_time = "2026-10-01T00:00:00Z"
    end_time = "2026-10-05T00:00:00Z"
    res = client.get(f"/analytics/factory?start_time={start_time}&end_time={end_time}")
    assert res.status_code == 200
    data = res.json()
    assert "start_time" in data
    assert "end_time" in data


def test_forecast_availability(client):
    """7. Test multi-step energy forecast endpoints."""
    res_factory = client.get("/forecast/factory?horizon_minutes=5")
    assert res_factory.status_code == 200
    data = res_factory.json()
    assert data["horizon_minutes"] == 5
    assert data["total_factory_forecast_kwh"] >= 0.0

    res_m = client.get("/forecast/machine/M02?horizon_minutes=3")
    assert res_m.status_code == 200
    assert res_m.json()["machine_id"] == "M02"


def test_savings_availability(client):
    """8. Test potential savings endpoint."""
    res = client.get("/savings/factory")
    assert res.status_code == 200
    data = res.json()
    assert "actual_energy_kwh" in data
    assert "expected_energy_kwh" in data
    assert "potential_savings_kwh" in data
    assert "potential_savings_inr" in data


def test_optimization_opportunities(client):
    """9. Test optimization opportunity engine endpoint."""
    res = client.get("/optimization/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert "total_opportunities" in data
    assert "opportunities" in data
    valid_categories = {
        "OPERATIONAL_DEVIATION",
        "IDLE_REDUCTION",
        "PROCESS_EFFICIENCY",
        "MAINTENANCE_ALIGNMENT",
        "THROUGHPUT_OPTIMIZATION",
    }
    for opp in data["opportunities"]:
        assert opp["category"] in valid_categories
        assert 0.0 <= opp["priority_score"] <= 100.0


def test_copilot_chat_and_fallback(client):
    """10. Test Energy Copilot endpoint with grounded fallback when Ollama is unavailable."""
    with patch("llm.ollama_client.ollama_client.is_available", return_value=False):
        res = client.post("/copilot/chat", json={"question": "Why is factory energy consumption above baseline?"})
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert len(data["answer"]) > 10
        assert data["grounded"] is True
        assert data["fallback_used"] is True
        assert data["intent"] in ("ENERGY_DEVIATION", "FACTORY_SUMMARY")


def test_dashboard_contract_compatibility(client):
    """11. Test that all endpoints required by the Streamlit dashboard respond correctly."""
    endpoints = [
        ("/demo/status", 200),
        ("/demo/factory", 200),
        ("/savings/states", 200),
        ("/demo/machine/M03", 200),
    ]
    for ep, expected_code in endpoints:
        res = client.get(ep)
        assert res.status_code == expected_code, f"Failed contract on {ep}"


def test_deterministic_demo_runner_behavior():
    """12. Test that run_pipeline_demo executes predictably with fixed seeds."""
    result = run_pipeline_demo(steps_per_phase=2, dt_seconds=1.0)
    assert result["telemetry_count"] == 48  # 4 machines x 2 steps x 6 phases = 48 records
    assert result["total_energy_kwh"] >= 0.0
    assert result["total_expected_kwh"] >= 0.0
    assert "copilot_answer" in result
    assert len(result["copilot_answer"]) > 0


# =========================================================================
# PHASE 12.1 RECONCILIATION TESTS
# =========================================================================

def test_reconciliation_1_factory_energy_internal(client):
    """1. Factory energy in /demo/factory matches sum of its machine_status list."""
    fac = client.get("/demo/factory").json()
    total_energy = fac["energy"]["actual_energy_kwh"]
    sum_machine_status = sum(m["energy_kwh"] for m in fac["machine_status"])
    assert abs(total_energy - sum_machine_status) < 1e-4, f"Mismatch: {total_energy} vs {sum_machine_status}"


def test_reconciliation_2_machine_to_factory_energy(client):
    """2. Individual /demo/machine/{id} actual energies sum to factory actual energy."""
    fac = client.get("/demo/factory").json()
    fac_energy = fac["energy"]["actual_energy_kwh"]
    machine_ids = ["M01", "M02", "M03", "M04"]
    m_energies = [client.get(f"/demo/machine/{m}").json()["actual_energy_kwh"] for m in machine_ids]
    sum_machines = sum(m_energies)
    assert abs(fac_energy - sum_machines) < 1e-4, f"Mismatch: {fac_energy} vs {sum_machines}"


def test_reconciliation_3_production_units(client):
    """3. Total production units in /demo/factory matches sum of /demo/machine/{id}."""
    fac = client.get("/demo/factory").json()
    fac_prod = fac["production"]["total_units"]
    machine_ids = ["M01", "M02", "M03", "M04"]
    sum_prod = sum(client.get(f"/demo/machine/{m}").json()["production_units"] for m in machine_ids)
    assert fac_prod == sum_prod, f"Mismatch: {fac_prod} vs {sum_prod}"


def test_reconciliation_4_state_energy_breakdown():
    """4. Machine state energy breakdown matches total machine actual energy."""
    from analytics.deviation import analyze_state_deviations
    from analytics.savings import compute_machine_savings
    recs = demo_state.get_demo_records("M01")
    if len(recs) >= 2:
        ms = compute_machine_savings(recs)
        states = analyze_state_deviations(recs)
        sum_state_energy = sum(s["actual_energy_kwh"] for s in states.values())
        assert abs(sum_state_energy - ms["actual_energy_kwh"]) < 1e-4


def test_reconciliation_5_same_analysis_window_across_modules(client):
    """5. Factory snapshot, machine snapshot, and copilot context use the same time window."""
    from llm.context_builder import context_builder
    fac = client.get("/demo/factory").json()
    ctx = context_builder.build_context("What is factory energy?")
    assert "time_window" in ctx["structured_data"]
    # Check that demo window bounds match active demo records
    if demo_state.has_active_demo_data():
        records = demo_state.get_demo_records()
        expected_start = min(r.timestamp for r in records).isoformat()
        expected_end = max(r.timestamp for r in records).isoformat()
        assert ctx["structured_data"]["time_window"]["start"] == expected_start
        assert ctx["structured_data"]["time_window"]["end"] == expected_end


def test_reconciliation_6_baseline_deviation_consistency(client):
    """6. Baseline, actual energy, and deviation satisfy deviation = actual - expected."""
    fac = client.get("/demo/factory").json()
    act = fac["energy"]["actual_energy_kwh"]
    exp = fac["energy"]["expected_energy_kwh"]
    dev = fac["deviation"]["deviation_kwh"]
    assert abs(dev - round(act - exp, 4)) < 1e-4

    # Check for individual machines
    for m in ["M01", "M02", "M03", "M04"]:
        m_data = client.get(f"/demo/machine/{m}").json()
        m_act = m_data["actual_energy_kwh"]
        m_exp = m_data["baseline_expected_energy_kwh"]
        m_dev = m_data["deviation_kwh"]
        assert abs(m_dev - round(m_act - m_exp, 4)) < 1e-4


def test_reconciliation_7_savings_deviation_consistency(client):
    """7. Potential savings equals max(0, deviation) and converts accurately to INR and CO2."""
    fac = client.get("/demo/factory").json()
    dev = fac["deviation"]["deviation_kwh"]
    sav_kwh = fac["savings"]["potential_savings_kwh"]
    sav_inr = fac["savings"]["potential_savings_inr"]
    sav_co2 = fac["savings"]["potential_co2_kg"]

    expected_kwh = max(0.0, dev)
    assert abs(sav_kwh - expected_kwh) < 1e-4
    assert abs(sav_inr - round(sav_kwh * 8.50, 2)) < 0.05
    assert abs(sav_co2 - round(sav_kwh * 0.716, 4)) < 1e-4


def test_reconciliation_8_copilot_demo_numerical_consistency(client):
    """8. Copilot narrative matches exact numerical values from /demo/factory and /demo/machine."""
    fac = client.get("/demo/factory").json()
    fac_act_str = f"{fac['energy']['actual_energy_kwh']:.2f}"
    
    with patch("llm.ollama_client.ollama_client.is_available", return_value=False):
        res_fac = client.post("/copilot/chat", json={"question": "What is the factory electrical energy consumption?"})
        assert res_fac.status_code == 200
        ans_fac = res_fac.json()["answer"]
        # Must reflect the factory actual energy
        assert str(fac['energy']['actual_energy_kwh']) in ans_fac or fac_act_str in ans_fac

        res_m01 = client.post("/copilot/chat", json={"question": "What is the status of machine M01?"})
        assert res_m01.status_code == 200
        ans_m01 = res_m01.json()["answer"]
        # Must NOT contain phantom jump of 25.57 kWh
        assert "25.57" not in ans_m01
        m01_act = client.get("/demo/machine/M01").json()["actual_energy_kwh"]
        assert str(m01_act) in ans_m01 or f"{m01_act:.4f}" in ans_m01


def test_reconciliation_9_no_cumulative_energy_double_counting():
    """9. Disjoint meter records across sessions are filtered and not counted as consumption."""
    from analytics.deviation import compute_machine_deviation_from_records
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 10, 0, 1, tzinfo=timezone.utc)
    t3 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # 2 hours later!
    t4 = datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)

    # Synthetic cross-session jump from 10.0 to 100.0 kWh
    records = [
        TelemetryRecord(timestamp=t1, machine_id="M01", power_kw=5.0, energy_kwh=10.0, machine_state=MachineState.RUNNING, production_count=1),
        TelemetryRecord(timestamp=t2, machine_id="M01", power_kw=5.0, energy_kwh=10.0014, machine_state=MachineState.RUNNING, production_count=1),
        TelemetryRecord(timestamp=t3, machine_id="M01", power_kw=5.0, energy_kwh=100.0, machine_state=MachineState.RUNNING, production_count=1),
        TelemetryRecord(timestamp=t4, machine_id="M01", power_kw=5.0, energy_kwh=100.0014, machine_state=MachineState.RUNNING, production_count=1),
    ]

    dev = compute_machine_deviation_from_records(records)
    # The jump of ~90 kWh across the 2-hour gap must NOT be counted as interval energy!
    # Expected energy: sum of the two 1s intervals = 0.0014 + 0.0014 = 0.0028 kWh
    assert dev["actual_energy_kwh"] < 1.0, f"Cross session jump double counted: {dev['actual_energy_kwh']} kWh"


def test_reconciliation_10_deterministic_repeated_demo_output():
    """10. Repeated demonstration runs produce mathematically identical results."""
    run1 = run_pipeline_demo(steps_per_phase=2, dt_seconds=1.0)
    run2 = run_pipeline_demo(steps_per_phase=2, dt_seconds=1.0)

    assert run1["total_energy_kwh"] == run2["total_energy_kwh"]
    assert run1["total_expected_kwh"] == run2["total_expected_kwh"]
    assert run1["total_production_units"] == run2["total_production_units"]
    assert run1["factory_sec"] == run2["factory_sec"]
    assert run1["copilot_answer"] == run2["copilot_answer"]

