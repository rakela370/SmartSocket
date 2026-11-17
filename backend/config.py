
"""Centralna konfiguracija pametne utičnice (simulacija)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SocketConfig:
    nominal_voltage_v: float = 220.0
    allowed_powers_w: tuple[int, ...] = (300, 600, 900)
    default_power_w: int = 300
    default_duration_s: int = 60
    max_duration_s: int = 24 * 60 * 60
    measurement_timeout_s: float = 1.0


CONFIG = SocketConfig()
