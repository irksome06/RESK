"""
Phase 4 MQTT Unit Tests (Mocked - No Broker Required).
Validates topic generation, serialization, publisher behavior, subscriber routing,
strict validation, safe error handling, and connection lifecycle.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

# Ensure person3_energy_intelligence is in PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import paho.mqtt.client as mqtt
from database.schemas import (
    TelemetryRecord,
    MachineHealthMessage,
    MachineActionMessage,
    MachineActionType,
    MachineState,
)
from mqtt.topics import (
    build_telemetry_topic,
    build_health_topic,
    build_action_topic,
    parse_factory_topic,
    validate_machine_id_for_topic,
    TOPIC_SUBSCRIBE_TELEMETRY,
    TOPIC_SUBSCRIBE_HEALTH,
    TOPIC_SUBSCRIBE_ACTION,
)
from mqtt.publisher import MQTTPublisher, ConnectionStatus
from mqtt.subscriber import MQTTSubscriber


# ==============================================================================
# 1. TOPIC BUILDER & PARSER TESTS
# ==============================================================================

def test_topic_builders():
    """Verify topic generation follows standard factory contract."""
    assert build_telemetry_topic("M01") == "factory/M01/telemetry"
    assert build_health_topic("M03") == "factory/M03/health"
    assert build_action_topic("M02") == "factory/M02/action"


def test_invalid_machine_id_for_topic():
    """Verify invalid machine IDs (empty, whitespace, wildcards) are rejected."""
    with pytest.raises(ValueError):
        validate_machine_id_for_topic("")
    with pytest.raises(ValueError):
        validate_machine_id_for_topic("   ")
    with pytest.raises(ValueError):
        validate_machine_id_for_topic("M01/sub")
    with pytest.raises(ValueError):
        validate_machine_id_for_topic("M01+")
    with pytest.raises(ValueError):
        validate_machine_id_for_topic("M01#")


def test_topic_parser():
    """Verify incoming topic parsing into (machine_id, message_type)."""
    assert parse_factory_topic("factory/M01/telemetry") == ("M01", "telemetry")
    assert parse_factory_topic("factory/M03/health") == ("M03", "health")
    assert parse_factory_topic("factory/M02/action") == ("M02", "action")

    # Invalid / unrecognized topics
    assert parse_factory_topic("factory/M01/unknown") == (None, None)
    assert parse_factory_topic("other/M01/telemetry") == (None, None)
    assert parse_factory_topic("factory/M01") == (None, None)
    assert parse_factory_topic("factory/M01/telemetry/extra") == (None, None)


# ==============================================================================
# 2. MESSAGE SERIALIZATION CONTRACT TESTS
# ==============================================================================

def test_telemetry_serialization():
    """Verify TelemetryRecord serializes cleanly to JSON matching schema contract."""
    record = TelemetryRecord(
        timestamp=datetime(2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc),
        machine_id="M01",
        power_kw=7.8,
        energy_kwh=125.6,
        machine_state=MachineState.RUNNING,
    )
    raw_json = record.model_dump_json()
    parsed = json.loads(raw_json)
    assert parsed["machine_id"] == "M01"
    assert parsed["power_kw"] == 7.8
    assert parsed["machine_state"] == "RUNNING"


def test_health_message_contract():
    """Verify Person 2 MachineHealthMessage validates and serializes correctly."""
    health = MachineHealthMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M03",
        health_score=72.0,
        anomaly_score=0.83,
        temperature_c=63.0,
        vibration=0.55,
        rpm=1420.0,
    )
    assert health.machine_id == "M03"
    assert health.health_score == 72.0
    json_str = health.model_dump_json()
    assert "72.0" in json_str


def test_action_message_contract():
    """Verify Person 1 MachineActionMessage validates and serializes correctly."""
    action = MachineActionMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        action=MachineActionType.SLEEP,
        duration_sec=300,
        reason="Machine idle for >5 minutes",
    )
    assert action.machine_id == "M01"
    assert action.action == MachineActionType.SLEEP
    assert action.duration_sec == 300


# ==============================================================================
# 3. MOCK PUBLISHER TESTS
# ==============================================================================

def test_publisher_publish_telemetry():
    """Verify publisher sends TelemetryRecord with QoS 1, retain=False to correct topic."""
    publisher = MQTTPublisher(host="mock-broker", port=1883, client_id="test_pub")
    publisher.client = MagicMock()

    # Mock successful publish return
    mock_res = MagicMock()
    mock_res.rc = mqtt.MQTT_ERR_SUCCESS
    publisher.client.publish.return_value = mock_res

    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=7.5,
        energy_kwh=100.0,
        machine_state=MachineState.RUNNING,
    )

    success = publisher.publish_telemetry(record)
    assert success is True
    publisher.client.publish.assert_called_once()
    call_args, call_kwargs = publisher.client.publish.call_args

    assert call_args[0] == "factory/M01/telemetry"
    assert "7.5" in call_args[1]
    assert call_kwargs["qos"] == 1
    assert call_kwargs["retain"] is False


def test_publisher_publish_health_and_action():
    """Verify publisher correctly routes health and action payloads."""
    publisher = MQTTPublisher(client_id="test_pub")
    publisher.client = MagicMock()
    mock_res = MagicMock()
    mock_res.rc = mqtt.MQTT_ERR_SUCCESS
    publisher.client.publish.return_value = mock_res

    # Health
    health = MachineHealthMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M03",
        health_score=80.0,
        anomaly_score=0.2,
    )
    assert publisher.publish_health(health) is True
    assert publisher.client.publish.call_args[0][0] == "factory/M03/health"

    # Action
    action = MachineActionMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        action=MachineActionType.WAKE,
    )
    assert publisher.publish_action(action) is True
    assert publisher.client.publish.call_args[0][0] == "factory/M01/action"


def test_publisher_connection_lifecycle():
    """Verify publisher lifecycle states (CONNECTING, CONNECTED, DISCONNECTED)."""
    publisher = MQTTPublisher(client_id="test_pub")
    assert publisher.status == ConnectionStatus.DISCONNECTED
    assert publisher.is_connected is False

    # Simulate connect success
    publisher._on_connect(None, None, None, 0)
    assert publisher.status == ConnectionStatus.CONNECTED
    assert publisher.is_connected is True

    # Simulate disconnect
    publisher._on_disconnect(None, None, 0)
    assert publisher.status == ConnectionStatus.DISCONNECTED
    assert publisher.is_connected is False


# ==============================================================================
# 4. MOCK SUBSCRIBER ROUTING & VALIDATION TESTS
# ==============================================================================

class MockMQTTMessage:
    """Helper to mock incoming paho.mqtt.client.MQTTMessage."""
    def __init__(self, topic: str, payload_bytes: bytes):
        self.topic = topic
        self.payload = payload_bytes


def test_subscriber_routing_telemetry():
    """Verify valid telemetry message triggers on_telemetry callback with TelemetryRecord."""
    received = []

    subscriber = MQTTSubscriber(on_telemetry=lambda r: received.append(r))
    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=8.1,
        energy_kwh=102.4,
        machine_state=MachineState.RUNNING,
    )
    msg = MockMQTTMessage(
        topic="factory/M01/telemetry",
        payload_bytes=record.model_dump_json().encode("utf-8"),
    )

    subscriber._on_message(None, None, msg)
    assert len(received) == 1
    assert isinstance(received[0], TelemetryRecord)
    assert received[0].machine_id == "M01"
    assert received[0].power_kw == 8.1
    assert subscriber.messages_valid_count == 1


def test_subscriber_routing_health_and_action():
    """Verify valid health and action messages trigger respective callbacks."""
    received_health = []
    received_action = []

    subscriber = MQTTSubscriber(
        on_health=lambda h: received_health.append(h),
        on_action=lambda a: received_action.append(a),
    )

    health_msg = MachineHealthMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M03",
        health_score=75.0,
        anomaly_score=0.4,
    )
    subscriber._on_message(
        None,
        None,
        MockMQTTMessage("factory/M03/health", health_msg.model_dump_json().encode("utf-8")),
    )
    assert len(received_health) == 1
    assert received_health[0].machine_id == "M03"

    action_msg = MachineActionMessage(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        action=MachineActionType.SLEEP,
        duration_sec=120,
    )
    subscriber._on_message(
        None,
        None,
        MockMQTTMessage("factory/M01/action", action_msg.model_dump_json().encode("utf-8")),
    )
    assert len(received_action) == 1
    assert received_action[0].action == MachineActionType.SLEEP


# ==============================================================================
# 5. ERROR HANDLING & RESILIENCE TESTS
# ==============================================================================

def test_subscriber_malformed_json_does_not_crash():
    """Verify malformed JSON does not crash subscriber and increments invalid count."""
    subscriber = MQTTSubscriber()
    msg = MockMQTTMessage("factory/M01/telemetry", b"INVALID_RAW_NON_JSON")

    # Should not raise exception
    subscriber._on_message(None, None, msg)
    assert subscriber.messages_invalid_count == 1


def test_subscriber_invalid_schema_payload():
    """Verify negative power or invalid states are rejected without crashing."""
    subscriber = MQTTSubscriber()
    # Invalid: negative power
    bad_payload = json.dumps({
        "timestamp": "2026-10-02T10:00:00Z",
        "machine_id": "M01",
        "power_kw": -100.0,
        "energy_kwh": 10.0,
        "machine_state": "RUNNING",
    }).encode("utf-8")
    msg = MockMQTTMessage("factory/M01/telemetry", bad_payload)

    subscriber._on_message(None, None, msg)
    assert subscriber.messages_invalid_count == 1


def test_subscriber_unknown_topic_ignored():
    """Verify message on unrecognized topic is safely ignored."""
    subscriber = MQTTSubscriber()
    msg = MockMQTTMessage("factory/M01/unrecognized_stream", b'{"key": "value"}')

    subscriber._on_message(None, None, msg)
    assert subscriber.messages_valid_count == 0


def test_subscriber_callback_exception_handled():
    """Verify exception raised inside user callback is caught and does not kill subscriber."""
    def faulty_callback(record):
        raise RuntimeError("Simulated failure in user analytics callback")

    subscriber = MQTTSubscriber(on_telemetry=faulty_callback)
    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc),
        machine_id="M01",
        power_kw=7.0,
        energy_kwh=10.0,
        machine_state=MachineState.RUNNING,
    )
    msg = MockMQTTMessage(
        topic="factory/M01/telemetry",
        payload_bytes=record.model_dump_json().encode("utf-8"),
    )

    # Must catch and not bubble up
    subscriber._on_message(None, None, msg)
    assert subscriber.messages_valid_count == 1  # Counted as validated before callback


def test_subscriber_subscriptions_registered_on_connect():
    """Verify all factory wildcards are subscribed with QoS 1 upon broker connection."""
    subscriber = MQTTSubscriber()
    subscriber.client = MagicMock()

    subscriber._on_connect(None, None, None, 0)
    assert subscriber.status == ConnectionStatus.CONNECTED
    subscriber.client.subscribe.assert_called_once()
    subs = subscriber.client.subscribe.call_args[0][0]
    expected_topics = [TOPIC_SUBSCRIBE_TELEMETRY, TOPIC_SUBSCRIBE_HEALTH, TOPIC_SUBSCRIBE_ACTION]
    assert [s[0] for s in subs] == expected_topics
    for s in subs:
        assert s[1] == 1  # QoS 1
