"""
Centralized MQTT Topic Architecture and Validation for Smart Manufacturing.
Prevents topic string scattering, guarantees topic sanity, and parses incoming payloads.
"""

from typing import Tuple, Optional
import re

# Central Wildcard Subscriptions
TOPIC_SUBSCRIBE_TELEMETRY = "factory/+/telemetry"
TOPIC_SUBSCRIBE_HEALTH = "factory/+/health"
TOPIC_SUBSCRIBE_ACTION = "factory/+/action"
ALL_FACTORY_SUBSCRIPTIONS = [
    TOPIC_SUBSCRIBE_TELEMETRY,
    TOPIC_SUBSCRIBE_HEALTH,
    TOPIC_SUBSCRIBE_ACTION,
]

# Regex for topic validation: factory/{machine_id}/{message_type}
_TOPIC_REGEX = re.compile(r"^factory/([^/+#]+)/(telemetry|health|action)$")


def validate_machine_id_for_topic(machine_id: str) -> str:
    """Validate and sanitize machine ID for MQTT topic path."""
    clean = machine_id.strip()
    if not clean or any(c in clean for c in "/+# \t\n\r"):
        raise ValueError(f"Invalid machine_id for MQTT topic: '{machine_id}'")
    return clean


def build_telemetry_topic(machine_id: str) -> str:
    """Builds standard telemetry publication topic: factory/{machine_id}/telemetry"""
    clean_id = validate_machine_id_for_topic(machine_id)
    return f"factory/{clean_id}/telemetry"


def build_health_topic(machine_id: str) -> str:
    """Builds standard machine health topic: factory/{machine_id}/health"""
    clean_id = validate_machine_id_for_topic(machine_id)
    return f"factory/{clean_id}/health"


def build_action_topic(machine_id: str) -> str:
    """Builds standard optimization action topic: factory/{machine_id}/action"""
    clean_id = validate_machine_id_for_topic(machine_id)
    return f"factory/{clean_id}/action"


def parse_factory_topic(topic: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses incoming MQTT topic into (machine_id, message_type).
    Returns (None, None) if topic does not conform to the factory contract.
    Example: 'factory/M01/telemetry' -> ('M01', 'telemetry')
    """
    match = _TOPIC_REGEX.match(topic)
    if not match:
        return None, None
    machine_id, message_type = match.groups()
    return machine_id, message_type
