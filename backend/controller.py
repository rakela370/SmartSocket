
"""Autonomna upravljačka logika pametne utičnice.

Modul ne zavisi od interneta, GUI-ja niti simulacionih scenarija.
Svaki novi podatak o snazi predaje se metodi receive_measurement(),
a tick() se poziva periodično radi zaštite i tajmera.
"""
from dataclasses import dataclass, replace
from enum import Enum
import math
import time
from typing import Callable

from .config import CONFIG
from .hardware import SimulatedIO


OVERLOAD_MESSAGE = (
    "Greška, tražite više od dozvoljene energije za isporuku."
)
MEASUREMENT_ERROR_MESSAGE = "Greška: neispravno mjerenje snage."
MEASUREMENT_TIMEOUT_MESSAGE = "Greška: mjerenje snage nije dostupno."


class SocketState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    TRIPPED = "TRIPPED"
    FINISHED = "FINISHED"


@dataclass
class SocketStatus:
    state: SocketState = SocketState.IDLE
    selected_power_w: int = CONFIG.default_power_w
    duration_s: int = CONFIG.default_duration_s
    remaining_s: float = float(CONFIG.default_duration_s)
    measured_power_w: float | None = None
    output_enabled: bool = False
    error_led_on: bool = False
    error_message: str = ""


class SmartSocketController:
    def __init__(
        self,
        io: SimulatedIO | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._io = io if io is not None else SimulatedIO()
        self._clock = clock
        self._status = SocketStatus()
        self._deadline: float | None = None
        self._last_measurement_at: float | None = None
        self._started_at: float | None = None

        # Bez napajanja na izlazu pri svakom pokretanju kontrolera.
        self._io.set_output(False)
        self._io.set_error_led(False)

    @property
    def status(self) -> SocketStatus:
        """Kopija statusa, kako drugi moduli ne bi mijenjali stanje."""
        return replace(self._status)

    @property
    def io(self) -> SimulatedIO:
        return self._io

    def configure(self, power_w: int, duration_s: int) -> None:
        if self._status.state == SocketState.RUNNING:
            raise RuntimeError("Ne može se mijenjati konfiguracija tokom rada.")
        if self._status.state == SocketState.TRIPPED:
            raise RuntimeError("Aktivna je greška. Prvo izvršite RESET.")
        if type(power_w) is not int or power_w not in CONFIG.allowed_powers_w:
            raise ValueError("Snaga mora biti 300, 600 ili 900 W.")
        if type(duration_s) is not int or not 1 <= duration_s <= CONFIG.max_duration_s:
            raise ValueError("Trajanje mora biti od 1 do 86400 sekundi.")

        self._io.set_output(False)
        self._io.set_error_led(False)
        self._deadline = None
        self._started_at = None
        self._last_measurement_at = None
        self._status = SocketStatus(
            state=SocketState.IDLE,
            selected_power_w=power_w,
            duration_s=duration_s,
            remaining_s=float(duration_s),
        )

    def start(self) -> None:
        if self._status.state != SocketState.IDLE:
            raise RuntimeError("START je dozvoljen samo iz stanja IDLE.")

        now = self._clock()
        self._started_at = now
        self._deadline = now + self._status.duration_s
        self._last_measurement_at = None
        self._status.remaining_s = float(self._status.duration_s)
        self._status.measured_power_w = None
        self._status.error_message = ""
        self._io.set_error_led(False)
        self._io.set_output(True)
        self._status.output_enabled = True
        self._status.error_led_on = False
        self._status.state = SocketState.RUNNING

    def receive_measurement(self, power_w: float) -> None:
        """Obrađuje jedno novo mjerenje aktivne snage (W)."""
        if self._status.state != SocketState.RUNNING:
            return

        # I prije primanja novog podatka provjeravamo da li je kasno.
        self.tick()
        if self._status.state != SocketState.RUNNING:
            return

        if (
            isinstance(power_w, bool)
            or not isinstance(power_w, (int, float))
            or not math.isfinite(power_w)
            or power_w < 0
        ):
            self._trip(MEASUREMENT_ERROR_MESSAGE)
            return

        self._last_measurement_at = self._clock()
        self._status.measured_power_w = float(power_w)

        if power_w > self._status.selected_power_w:
            self._trip(OVERLOAD_MESSAGE)

    def tick(self) -> None:
        """Periodična provjera trajanja i dostupnosti mjerenja."""
        if self._status.state != SocketState.RUNNING:
            return

        now = self._clock()
        assert self._deadline is not None
        assert self._started_at is not None
        self._status.remaining_s = max(0.0, self._deadline - now)

        if now >= self._deadline:
            self._io.set_output(False)
            self._status.output_enabled = False
            self._status.state = SocketState.FINISHED
            return

        reference = (
            self._last_measurement_at
            if self._last_measurement_at is not None
            else self._started_at
        )
        if now - reference >= CONFIG.measurement_timeout_s:
            self._trip(MEASUREMENT_TIMEOUT_MESSAGE)

    def stop(self) -> None:
        """STOP ne smije obrisati već aktiviranu grešku."""
        self._io.set_output(False)
        self._status.output_enabled = False

        if self._status.state == SocketState.TRIPPED:
            return

        self._io.set_error_led(False)
        self._status.error_led_on = False
        self._status.error_message = ""
        self._status.measured_power_w = None
        self._status.remaining_s = float(self._status.duration_s)
        self._status.state = SocketState.IDLE
        self._deadline = None
        self._started_at = None
        self._last_measurement_at = None

    def reset(self) -> None:
        """RESET je dozvoljen samo kada utičnica nije RUNNING."""
        if self._status.state == SocketState.RUNNING:
            raise RuntimeError("Prije RESET komande zaustavite uređaj.")

        self._io.set_output(False)
        self._io.set_error_led(False)
        self._deadline = None
        self._started_at = None
        self._last_measurement_at = None
        self._status = SocketStatus(
            selected_power_w=self._status.selected_power_w,
            duration_s=self._status.duration_s,
            remaining_s=float(self._status.duration_s),
        )

    def _trip(self, message: str) -> None:
        # Prvo fizička komanda isključenja, zatim promjena stanja.
        self._io.set_output(False)
        self._status.output_enabled = False
        self._io.set_error_led(True)
        self._status.error_led_on = True
        self._status.error_message = message
        self._status.state = SocketState.TRIPPED
