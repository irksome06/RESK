"""
Production-Grade MQTT Publisher for Industrial Telemetry, Health, and Action Events.
Serializes validated Pydantic models to JSON and publishes over standardized topics with QoS 1.
"""

import logging
from enum import Enum
from typing import Optional, Union, Dict, Any
import paho.mqtt.client as mqtt

from database.schemas import TelemetryRecord, MachineHealthMessage, MachineActionMessage
from mqtt.topics import build_telemetry_topic, build_health_topic, build_action_topic
from simulator.config import settings

logger = logging.getLogger("mqtt.publisher")


class ConnectionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"


class MQTTPublisher:
    """
    Manages persistent connection to MQTT broker and publishes validated machine events.
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
        retain: Optional[bool] = None,
    ):
        self.host = host or settings.MQTT_BROKER_HOST
        self.port = port or settings.MQTT_BROKER_PORT
        self.client_id = client_id or f"{settings.MQTT_CLIENT_ID}_pub"
        self.username = username or settings.MQTT_USERNAME
        self.password = password or settings.MQTT_PASSWORD
        self.keepalive = keepalive if keepalive is not None else settings.MQTT_KEEPALIVE
        self.qos = qos if qos is not None else settings.MQTT_QOS
        self.retain = retain if retain is not None else settings.MQTT_RETAIN

        self.status = ConnectionStatus.DISCONNECTED

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

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

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
            logger.info("MQTT Publisher connected to %s:%s (client_id=%s)", self.host, self.port, self.client_id)
        else:
            self.status = ConnectionStatus.DISCONNECTED
            logger.error("MQTT Publisher connection refused with code: %s", reason_code)

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        self.status = ConnectionStatus.DISCONNECTED
        logger.info("MQTT Publisher disconnected from broker")

    def _on_publish(self, client, userdata, mid, *args, **kwargs):
        logger.debug("MQTT message published (mid=%s)", mid)

    def connect(self) -> bool:
        """
        Connects to the MQTT broker asynchronously and starts the network thread.
        """
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info("MQTT Publisher connecting to %s:%s...", self.host, self.port)
            self.client.connect(self.host, self.port, keepalive=self.keepalive)
            self.client.loop_start()
            return True
        except Exception as e:
            self.status = ConnectionStatus.DISCONNECTED
            logger.error("Failed to connect to MQTT broker %s:%s: %s", self.host, self.port, e)
            return False

    def disconnect(self) -> None:
        """Disconnect cleanly and stop background loop."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            logger.warning("Error during publisher disconnect: %s", e)
        finally:
            self.status = ConnectionStatus.DISCONNECTED
            logger.info("MQTT Publisher stopped")

    def publish_telemetry(self, record: Union[TelemetryRecord, Dict[str, Any]]) -> bool:
        """
        Validates, serializes, and publishes a TelemetryRecord to factory/{machine_id}/telemetry.
        """
        try:
            # Enforce validation against canonical contract
            if not isinstance(record, TelemetryRecord):
                validated_record = TelemetryRecord.model_validate(record)
            else:
                validated_record = record

            topic = build_telemetry_topic(validated_record.machine_id)
            payload = validated_record.model_dump_json()

            res = self.client.publish(topic, payload, qos=self.qos, retain=self.retain)
            if res.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("Published telemetry for %s to %s", validated_record.machine_id, topic)
                return True
            else:
                logger.warning("Failed to publish telemetry to %s (rc=%s)", topic, res.rc)
                return False
        except Exception as e:
            logger.error("Error validating/publishing telemetry: %s", e)
            return False

    def publish_health(self, health: Union[MachineHealthMessage, Dict[str, Any]]) -> bool:
        """
        Validates, serializes, and publishes health diagnostic to factory/{machine_id}/health.
        """
        try:
            if not isinstance(health, MachineHealthMessage):
                validated_health = MachineHealthMessage.model_validate(health)
            else:
                validated_health = health

            topic = build_health_topic(validated_health.machine_id)
            payload = validated_health.model_dump_json()

            res = self.client.publish(topic, payload, qos=self.qos, retain=self.retain)
            return res.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error("Error validating/publishing machine health: %s", e)
            return False

    def publish_action(self, action: Union[MachineActionMessage, Dict[str, Any]]) -> bool:
        """
        Validates, serializes, and publishes an optimization action to factory/{machine_id}/action.
        """
        try:
            if not isinstance(action, MachineActionMessage):
                validated_action = MachineActionMessage.model_validate(action)
            else:
                validated_action = action

            topic = build_action_topic(validated_action.machine_id)
            payload = validated_action.model_dump_json()

            res = self.client.publish(topic, payload, qos=self.qos, retain=self.retain)
            return res.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error("Error validating/publishing optimization action: %s", e)
            return False
