"""
Resilient MQTT Subscriber for Industrial Telemetry, Health, and Action Messages.
Features strict Pydantic payload validation, topic routing, safe malformed message handling,
and automatic reconnection with exponential backoff.
"""

import logging
from enum import Enum
from typing import Optional, Callable
import paho.mqtt.client as mqtt
from pydantic import ValidationError

from database.schemas import TelemetryRecord, MachineHealthMessage, MachineActionMessage
from mqtt.topics import (
    TOPIC_SUBSCRIBE_TELEMETRY,
    TOPIC_SUBSCRIBE_HEALTH,
    TOPIC_SUBSCRIBE_ACTION,
    parse_factory_topic,
)
from simulator.config import settings

logger = logging.getLogger("mqtt.subscriber")


class ConnectionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"


class MQTTSubscriber:
    """
    Subscribes to factory topic patterns, validates incoming messages against Pydantic schemas,
    and routes them to dedicated type-safe application callbacks.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: Optional[int] = None,
        qos: Optional[int] = None,
        on_telemetry: Optional[Callable[[TelemetryRecord], None]] = None,
        on_health: Optional[Callable[[MachineHealthMessage], None]] = None,
        on_action: Optional[Callable[[MachineActionMessage], None]] = None,
    ):
        self.host = host or settings.MQTT_BROKER_HOST
        self.port = port or settings.MQTT_BROKER_PORT
        self.client_id = client_id or f"{settings.MQTT_CLIENT_ID}_sub"
        self.username = username or settings.MQTT_USERNAME
        self.password = password or settings.MQTT_PASSWORD
        self.keepalive = keepalive if keepalive is not None else settings.MQTT_KEEPALIVE
        self.qos = qos if qos is not None else settings.MQTT_QOS

        # Callbacks
        self.on_telemetry_callback = on_telemetry
        self.on_health_callback = on_health
        self.on_action_callback = on_action

        self.status = ConnectionStatus.DISCONNECTED

        # Statistics / Observability
        self.messages_received_count = 0
        self.messages_valid_count = 0
        self.messages_invalid_count = 0

        # Initialize Paho client compatible with Paho 2.x and 1.x
        if hasattr(mqtt, "CallbackAPIVersion") and hasattr(mqtt.CallbackAPIVersion, "VERSION2"):
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
            )
        else:
            self.client = mqtt.Client(client_id=self.client_id)

        if self.username:
            self.client.username_pw_set(self.username, self.password)

        # Configure automatic reconnection backoff (min 1s, max 30s)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    @property
    def is_connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED

    def _on_connect(self, client, userdata, flags, reason_code, *args, **kwargs):
        is_success = False
        if hasattr(reason_code, "is_failure"):
            is_success = not reason_code.is_failure
        else:
            is_success = (reason_code == 0)

        if is_success:
            self.status = ConnectionStatus.CONNECTED
            logger.info("MQTT Subscriber connected to %s:%s (client_id=%s)", self.host, self.port, self.client_id)

            # Subscribe to factory topic wildcards with QoS 1
            subscriptions = [
                (TOPIC_SUBSCRIBE_TELEMETRY, self.qos),
                (TOPIC_SUBSCRIBE_HEALTH, self.qos),
                (TOPIC_SUBSCRIBE_ACTION, self.qos),
            ]
            self.client.subscribe(subscriptions)
            logger.info("Subscribed to MQTT topics: %s", [s[0] for s in subscriptions])
        else:
            self.status = ConnectionStatus.DISCONNECTED
            logger.error("MQTT Subscriber connection refused with code: %s", reason_code)

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        self.status = ConnectionStatus.DISCONNECTED
        logger.info("MQTT Subscriber disconnected from broker")

    def _on_message(self, client, userdata, msg):
        """
        Processes incoming raw MQTT message, validates payload, and dispatches to callback.
        Guarantees that malformed messages or callback errors never crash the thread.
        """
        self.messages_received_count += 1
        topic = msg.topic

        try:
            payload_str = msg.payload.decode("utf-8")
        except UnicodeDecodeError as e:
            self.messages_invalid_count += 1
            logger.warning("Rejected non-UTF8 payload on topic %s: %s", topic, e)
            return

        machine_id, message_type = parse_factory_topic(topic)
        if not machine_id or not message_type:
            logger.warning("Received message on unrecognized topic '%s', ignoring", topic)
            return

        try:
            if message_type == "telemetry":
                record = TelemetryRecord.model_validate_json(payload_str)
                self.messages_valid_count += 1
                if self.on_telemetry_callback:
                    try:
                        self.on_telemetry_callback(record)
                    except Exception as cb_err:
                        logger.error("Unhandled exception in on_telemetry callback: %s", cb_err)

            elif message_type == "health":
                health = MachineHealthMessage.model_validate_json(payload_str)
                self.messages_valid_count += 1
                if self.on_health_callback:
                    try:
                        self.on_health_callback(health)
                    except Exception as cb_err:
                        logger.error("Unhandled exception in on_health callback: %s", cb_err)

            elif message_type == "action":
                action = MachineActionMessage.model_validate_json(payload_str)
                self.messages_valid_count += 1
                if self.on_action_callback:
                    try:
                        self.on_action_callback(action)
                    except Exception as cb_err:
                        logger.error("Unhandled exception in on_action callback: %s", cb_err)

        except ValidationError as val_err:
            self.messages_invalid_count += 1
            logger.warning(
                "Payload validation failed on topic '%s' for machine '%s': %s",
                topic,
                machine_id,
                val_err.errors(),
            )
        except Exception as unk_err:
            self.messages_invalid_count += 1
            logger.error("Unexpected error processing MQTT message on '%s': %s", topic, unk_err)

    def start(self) -> bool:
        """Connects and starts background network processing loop."""
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info("Starting MQTT Subscriber loop for %s:%s...", self.host, self.port)
            self.client.connect(self.host, self.port, keepalive=self.keepalive)
            self.client.loop_start()
            return True
        except Exception as e:
            self.status = ConnectionStatus.DISCONNECTED
            logger.error("Failed to start MQTT subscriber: %s", e)
            return False

    def stop(self) -> None:
        """Stops network processing loop and cleanly disconnects."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            logger.warning("Error during subscriber shutdown: %s", e)
        finally:
            self.status = ConnectionStatus.DISCONNECTED
            logger.info("MQTT Subscriber stopped")
