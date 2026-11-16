
from enum import Enum
from dataclasses import dataclass
from .config import CONFIG


class SocketState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    TRIPPED = "TRIPPED"
    FINISHED = "FINISHED"


@dataclass
class SocketStatus:
    state: SocketState = SocketState.IDLE
    selected_power: int = 300
    duration_seconds: int = 60
    remaining_seconds: float = 60.0
    measured_power: float = 0.0
    output_enabled: bool = False
    error_message: str = ""


class SmartSocketController:

    def __init__(self):
        self.status = SocketStatus()

    def configure(self, power: int, duration: int):
        if self.status.state == SocketState.RUNNING:
            raise RuntimeError(
                "Nije dozvoljena konfiguracija tokom rada."
            )

        if self.status.state == SocketState.TRIPPED:
            raise RuntimeError(
                "Prvo resetujte gresku."
            )

        if power not in CONFIG.allowed_powers:
            raise ValueError("Nedozvoljena snaga.")

        if not 1 <= duration <= CONFIG.max_duration_seconds:
            raise ValueError("Neispravno trajanje.")

        self.status.selected_power = power
        self.status.duration_seconds = duration
        self.status.remaining_seconds = float(duration)
        self.status.measured_power = 0.0
        self.status.output_enabled = False
        self.status.error_message = ""
        self.status.state = SocketState.IDLE

    def start(self):
        if self.status.state != SocketState.IDLE:
            raise RuntimeError(
                "Uredjaj nije spreman za pokretanje."
            )

        self.status.remaining_seconds = float(
            self.status.duration_seconds
        )
        self.status.measured_power = 0.0
        self.status.output_enabled = True
        self.status.state = SocketState.RUNNING

    def update(self, measured_power: float, elapsed: float):
        if self.status.state != SocketState.RUNNING:
            return

        if (
            not isinstance(measured_power, (int, float))
            or not isinstance(elapsed, (int, float))
        ):
            self.trip("Neispravni podaci mjerenja.")
            return

        import math

        if (
            not math.isfinite(measured_power)
            or measured_power < 0
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            self.trip("Neispravni podaci mjerenja.")
            return

        self.status.measured_power = measured_power

        if measured_power > self.status.selected_power:
            self.trip(
                "Greska, trazite vise od dozvoljene "
                "energije za isporuku."
            )
            return

        self.status.remaining_seconds = max(
            0.0,
            self.status.remaining_seconds - elapsed
        )

        if self.status.remaining_seconds <= 0:
            self.status.output_enabled = False
            self.status.state = SocketState.FINISHED

    def trip(self, message: str):
        self.status.output_enabled = False
        self.status.state = SocketState.TRIPPED
        self.status.error_message = message

    def stop(self):
        self.status.output_enabled = False
        self.status.measured_power = 0.0
        self.status.state = SocketState.IDLE

    def reset(self):
        self.status = SocketStatus()
