
from dataclasses import dataclass

@dataclass(frozen=True)
class SocketConfig:
    nominal_voltage: float = 220.0
    allowed_powers: tuple[int, ...] = (300, 600, 900)
    max_duration_seconds: int = 24 * 60 * 60

CONFIG = SocketConfig()
