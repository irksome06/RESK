"""
Demonstration runner for Phase 4 MQTT pipeline.
Simulates end-to-end telemetry, health, and action publishing/subscribing.
Gracefully handles offline broker scenarios with helpful setup guidance.
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

# Ensure person3_energy_intelligence is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.schemas import (
    TelemetryRecord,
    MachineHealthMessage,
    MachineActionMessage,
    MachineActionType,
)
from mqtt.publisher import MQTTPublisher
from mqtt.subscriber import MQTTSubscriber
from simulator.machine_simulator import FactorySimulator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mqtt.demo")


def main():
    received_telemetry = []
    received_health = []
    received_actions = []

    def handle_telemetry(record: TelemetryRecord):
        received_telemetry.append(record)
        logger.info(
            "-> Subscriber received Telemetry for %s: Power=%.2fkW, State=%s, Health=%.1f",
            record.machine_id,
            record.power_kw,
            record.machine_state.value,
            record.health_score or 0.0,
        )

    def handle_health(health: MachineHealthMessage):
        received_health.append(health)
        logger.info(
            "-> Subscriber received Person 2 Health Alert for %s: Health=%.1f, Anomaly=%.2f, Temp=%.1fC",
            health.machine_id,
            health.health_score,
            health.anomaly_score,
            health.temperature_c or 0.0,
        )

    def handle_action(action: MachineActionMessage):
        received_actions.append(action)
        logger.info(
            "-> Subscriber received Person 1 Optimization Action for %s: %s (duration=%ss, reason='%s')",
            action.machine_id,
            action.action.value,
            action.duration_sec,
            action.reason,
        )

    logger.info("Initializing MQTT Subscriber and Publisher...")
    subscriber = MQTTSubscriber(
        client_id="demo_subscriber",
        on_telemetry=handle_telemetry,
        on_health=handle_health,
        on_action=handle_action,
    )
    publisher = MQTTPublisher(client_id="demo_publisher")

    # Attempt connection
    sub_started = subscriber.start()
    pub_connected = publisher.connect()

    if not sub_started or not pub_connected:
        logger.warning("\n========================================================")
        logger.warning("Could not connect to MQTT broker on %s:%s.", publisher.host, publisher.port)
        logger.warning("To start a local Mosquitto broker:")
        logger.warning("  Using Docker:   docker compose up -d mosquitto")
        logger.warning("  Using Homebrew: brew services start mosquitto")
        logger.warning("========================================================\n")
        subscriber.stop()
        publisher.disconnect()
        return 1

    time.sleep(1.0)  # Brief wait for network loop handshake
    logger.info("Broker connection active. Initializing FactorySimulator...")
    simulator = FactorySimulator(seed=42)

    # 1. Publish 3 steps of simulated factory telemetry (4 machines x 3 = 12 records)
    logger.info("Generating and publishing factory telemetry...")
    for step_idx in range(1, 4):
        records = simulator.step(dt_seconds=1.0)
        for r in records:
            publisher.publish_telemetry(r)
        time.sleep(0.2)

    # 2. Publish simulated Person 2 Machine Health Alert (e.g. M03 vibration degradation)
    logger.info("Publishing Person 2 Machine Health message...")
    health_msg = MachineHealthMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M03",
        health_score=71.5,
        anomaly_score=0.82,
        temperature_c=64.2,
        vibration=0.58,
        rpm=1410.0,
    )
    publisher.publish_health(health_msg)
    time.sleep(0.2)

    # 3. Publish simulated Person 1 Optimization Action (e.g. M01 idle sleep command)
    logger.info("Publishing Person 1 Optimization Action...")
    action_msg = MachineActionMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        action=MachineActionType.SLEEP,
        duration_sec=300,
        reason="Machine idle for >5 minutes, entering eco sleep",
    )
    publisher.publish_action(action_msg)

    # Allow background loop to process messages
    time.sleep(1.5)

    logger.info("\n=== DEMO SUMMARY ===")
    logger.info("Telemetry messages processed by subscriber: %d", len(received_telemetry))
    logger.info("Health messages processed by subscriber:    %d", len(received_health))
    logger.info("Action messages processed by subscriber:    %d", len(received_actions))

    subscriber.stop()
    publisher.disconnect()
    logger.info("Clean shutdown completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
