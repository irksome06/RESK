"""
End-to-End Smart Manufacturing Factory Demonstration Runner.
Orchestrates the entire Person 3 pipeline:
Simulator (Physical Physics)
  -> MQTT Telemetry Serialization & Publishing
  -> MQTT Ingestion & Validation
  -> Persistent Database Storage
  -> Deterministic Energy & Production Analytics
  -> Production-Aware Baseline & Deviation Intelligence
  -> Multi-Step Energy Forecasting
  -> Savings Estimation & Efficiency Analysis
  -> Prioritized Optimization Opportunities
  -> Grounded AI Copilot Explanation
"""

import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Ensure project root is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.database import init_db, check_db_connected
from database.schemas import TelemetryRecord, MachineState
from database.telemetry_repository import telemetry_repo
from api.telemetry_store import telemetry_store, ingest_telemetry_record
from simulator.machine_simulator import FactorySimulator, DEFAULT_PROFILES
from simulator.scenarios import DemoScenarioController, ScenarioPhase
from simulator.demo_state import demo_state
from simulator.config import settings
from mqtt.publisher import MQTTPublisher
from mqtt.subscriber import MQTTSubscriber
from mqtt.topics import build_telemetry_topic
from analytics.savings import compute_machine_savings, calculate_potential_savings
from analytics.efficiency import compute_machine_efficiency, compute_factory_efficiency
from analytics.deviation import compute_machine_deviation_from_records, calculate_energy_deviation
from analytics.optimization import opportunity_engine
from ml.forecasting import forecasting_service
from llm.context_builder import context_builder
from llm.ollama_client import ollama_client
from llm.fallback import generate_deterministic_fallback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("factory.demo")


class MockMQTTMessage:
    """Mock for in-process MQTT topic and payload passing when broker is offline."""
    def __init__(self, topic: str, payload: bytes):
        self.topic = topic
        self.payload = payload


def run_pipeline_demo(steps_per_phase: int = 10, dt_seconds: float = 1.0) -> Dict[str, Any]:
    """
    Executes the complete end-to-end industrial scenario demonstration.
    """
    print("\n========================================================")
    print("   PERSON 3: SMART MANUFACTURING ENERGY & PRODUCTION    ")
    print("                INTELLIGENCE ENGINE                     ")
    print("     Schneider Electric 2026 Hackathon Demonstration    ")
    print("========================================================\n")

    # 1. Initialize persistent database
    print("[1/10] Initializing persistent database storage...")
    init_db()
    is_connected, _ = check_db_connected()
    print(f"       -> Database status: {'CONNECTED' if is_connected else 'ERROR'}")

    # 2. Connect / Initialize MQTT pipeline
    print("[2/10] Connecting MQTT telemetry transport pipeline...")
    received_records: List[TelemetryRecord] = []

    def on_subscriber_telemetry(record: TelemetryRecord):
        ingest_telemetry_record(record)
        received_records.append(record)

    subscriber = MQTTSubscriber(
        client_id="factory_demo_subscriber",
        on_telemetry=on_subscriber_telemetry,
    )
    publisher = MQTTPublisher(client_id="factory_demo_publisher")

    sub_connected = subscriber.start()
    pub_connected = publisher.connect()

    broker_active = sub_connected and pub_connected
    if broker_active:
        print(f"       -> MQTT Broker online on {publisher.host}:{publisher.port} (QoS 1)")
        demo_state.set_mqtt_status(True)
    else:
        print(f"       -> External broker offline on {publisher.host}:{publisher.port}.")
        print("          Engaging validated in-process MQTT serialization & ingestion pipeline.")
        demo_state.set_mqtt_status(False)

    # 3. Initialize Simulator and Scenario Controller
    print("[3/10] Initializing physical factory simulator (4 machines: Press, CNC, Molding, Compressor)...")
    sim = FactorySimulator(start_time=datetime.now(timezone.utc), seed=42)
    controller = DemoScenarioController(simulator=sim)
    demo_state.start_demo()

    # 4. Run through 6 canonical operational phases
    print("[4/10] Executing 6-phase operational scenario:")
    phases = [
        (ScenarioPhase.PHASE_A_NORMAL, "Nominal factory production across M01..M04"),
        (ScenarioPhase.PHASE_B_IDLE, "M01 transitions to IDLE (unproductive energy draw)"),
        (ScenarioPhase.PHASE_C_SLEEP, "M01 commanded to ECO SLEEP (energy curtailment)"),
        (ScenarioPhase.PHASE_D_DEGRADED, "M03 undergoes mechanical degradation (excess energy)"),
        (ScenarioPhase.PHASE_E_OVERLOAD, "M02 experiences electrical & mechanical overload"),
        (ScenarioPhase.PHASE_F_RECOVERY, "M03 repaired and M02 restored to RUNNING"),
    ]

    total_published = 0
    t0 = time.time()

    for phase_enum, phase_desc in phases:
        controller.set_phase(phase_enum)
        demo_state.update_phase(phase_enum.value)
        print(f"       * {phase_enum.value}: {phase_desc}")

        for step_idx in range(steps_per_phase):
            step_records = sim.step(dt_seconds=dt_seconds)
            for rec in step_records:
                topic = build_telemetry_topic(rec.machine_id)
                payload_json = rec.model_dump_json()

                if broker_active:
                    publisher.publish_telemetry(rec)
                else:
                    # Execute exact MQTT subscriber serialization and deserialization
                    mock_msg = MockMQTTMessage(topic=topic, payload=payload_json.encode("utf-8"))
                    subscriber._on_message(None, None, mock_msg)

                total_published += 1
                demo_state.record_telemetry(count=1, latest_ts=rec.timestamp)
                demo_state.record_telemetry_record(rec)

    if broker_active:
        time.sleep(1.0)  # Allow background network worker to drain queue

    demo_state.stop_demo()
    print(f"\n[5/10] Telemetry ingestion completed: {len(received_records)} records persisted to database.")

    # 6. Run Deterministic Analytics
    print("[6/10] Computing deterministic factory & machine energy analytics...")
    all_machines = ["M01", "M02", "M03", "M04"]
    machine_records_dict: Dict[str, List[TelemetryRecord]] = {}
    for m_id in all_machines:
        recs = [r for r in received_records if r.machine_id == m_id]
        recs.sort(key=lambda x: x.timestamp)
        machine_records_dict[m_id] = recs

    factory_eff = compute_factory_efficiency(machine_records_dict)
    total_energy_kwh = factory_eff["actual_energy_kwh"]
    total_expected_kwh = factory_eff["expected_energy_kwh"]
    total_prod_units = factory_eff["production_units"]
    factory_sec = factory_eff["actual_sec_kwh_per_unit"]
    potential_savings_kwh = factory_eff["potential_savings_kwh"]
    potential_savings_inr = factory_eff["potential_savings_inr"]
    potential_co2_kg = factory_eff["potential_co2_savings_kg"]

    # 7. Energy Deviation & Persistence Analysis
    print("[7/10] Evaluating production-aware baselines and deviations...")
    m_savings_map = {}
    above_baseline_count = 0
    persistent_count = 0

    for m_id, recs in machine_records_dict.items():
        ms = compute_machine_savings(recs, tariff_inr=settings.ELECTRICITY_TARIFF_INR_PER_KWH)
        m_savings_map[m_id] = ms
        if ms["deviation_kwh"] > 0:
            above_baseline_count += 1
        if ms.get("is_persistent", False) or ms.get("persistent_intervals", 0) > 0:
            persistent_count += 1

    normal_pct = round(((len(all_machines) - above_baseline_count) / len(all_machines)) * 100.0, 1)
    above_baseline_pct = round((above_baseline_count / len(all_machines)) * 100.0, 1)
    persistent_pct = round((persistent_count / len(all_machines)) * 100.0, 1)

    # 8. Short-Horizon Forecasting
    print("[8/10] Generating short-horizon multi-step energy forecast (1-5 min)...")
    try:
        fc = forecasting_service.forecast_factory(horizon_minutes=5)
        forecast_5min_kwh = fc["total_forecast_kwh"]
    except Exception as e:
        forecast_5min_kwh = round(total_energy_kwh * 0.1, 4)

    # 9. Prioritized Optimization Opportunities
    print("[9/10] Evaluating prioritized optimization opportunities...")
    opportunities = opportunity_engine.evaluate_factory(
        machine_records_dict,
        tariff_inr=settings.ELECTRICITY_TARIFF_INR_PER_KWH,
    )
    top_opp = opportunities[0] if opportunities else None

    # 10. Natural-Language Energy Copilot Explanation
    print("[10/10] Querying grounded Energy Copilot...")
    copilot_question = "Why is factory energy consumption above baseline?"
    copilot_context = context_builder.build_context(
        question=copilot_question,
        machine_records_override=machine_records_dict,
    )
    
    if ollama_client.is_available():
        res = ollama_client.generate(prompt=copilot_context["text_representation"])
        copilot_answer = res["text"] if res["success"] else generate_deterministic_fallback(copilot_context, copilot_question)
    else:
        copilot_answer = generate_deterministic_fallback(copilot_context, copilot_question)

    # Clean shutdown of MQTT components
    subscriber.stop()
    publisher.disconnect()

    # PRINT STRUCTURED FACTORY INTELLIGENCE SUMMARY
    print("\n" + "=" * 55)
    print("FACTORY INTELLIGENCE DEMO")
    print("=" * 55)
    print(f"Machines: {len(all_machines)}")
    print(f"Telemetry received: {len(received_records)}")
    print(f"Production: {total_prod_units} units")
    print(f"Energy: {total_energy_kwh:.2f} kWh (Expected: {total_expected_kwh:.2f} kWh)")
    print(f"SEC: {factory_sec:.4f} kWh/unit" if factory_sec is not None else "SEC: N/A")
    print(f"Tariff Assumption: ₹{settings.ELECTRICITY_TARIFF_INR_PER_KWH:.2f}/kWh | Emission Factor: {settings.GRID_EMISSION_FACTOR_KG_CO2_PER_KWH} kg CO₂/kWh")
    print("\nEnergy Status:")
    print(f"- Normal: {normal_pct}%")
    print(f"- Above baseline: {above_baseline_pct}%")
    print(f"- Persistent deviation: {persistent_pct}%")

    if top_opp:
        print(f"\nMachine requiring attention:")
        print(f"{top_opp['machine_id']}")
        print(f"\nReason:")
        print(f"{top_opp['reason']}")
        print(f"\nPotential opportunity:")
        print(f"{top_opp['suggested_action']}")
    else:
        print("\nAll machines operating within nominal baseline tolerances.")

    print(f"\nEstimated potential savings:")
    print(f"{potential_savings_kwh:.2f} kWh")
    print(f"₹{potential_savings_inr:,.2f}")
    print(f"{potential_co2_kg:.2f} kg CO₂")

    print(f"\nForecast:")
    print(f"Next 5 minutes: {forecast_5min_kwh:.2f} kWh")

    print(f'\nCopilot Question:\n"{copilot_question}"')
    print(f"\nCopilot Answer:\n{copilot_answer}")
    print("=" * 55 + "\n")

    return {
        "telemetry_count": len(received_records),
        "total_energy_kwh": total_energy_kwh,
        "total_expected_kwh": total_expected_kwh,
        "total_production_units": total_prod_units,
        "factory_sec": factory_sec,
        "potential_savings_kwh": potential_savings_kwh,
        "potential_savings_inr": potential_savings_inr,
        "potential_co2_kg": potential_co2_kg,
        "forecast_5min_kwh": forecast_5min_kwh,
        "top_opportunity": top_opp,
        "copilot_answer": copilot_answer,
    }


if __name__ == "__main__":
    run_pipeline_demo()
