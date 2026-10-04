from enum import Enum


class MachineState(str, Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    SLEEP = "SLEEP"
    DEGRADED = "DEGRADED"
    OVERLOAD = "OVERLOAD"
