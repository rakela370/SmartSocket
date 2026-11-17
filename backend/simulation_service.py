"""Offline device model: local controls, virtual load and simulated power meter.

The selected limit belongs to the controller; the requested load belongs to
an independent simulated consumer. The simulator never bypasses the controller.
"""
import math
import threading
import time
from typing import Callable

from .config import CONFIG
from .controller import SmartSocketController, SocketState


class SimulationService:
    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        sample_period_s: float = 0.1,
    ) -> None:
        if not 0 < sample_period_s < CONFIG.measurement_timeout_s:
            raise ValueError("Period uzorkovanja mora biti kraci od watchdog praga.")
        self._clock = clock
        self._controller = SmartSocketController(clock=clock)
        self._requested_power_w = 0.0
        self._energy_wh = 0.0
        self._last_step_at = clock()
        self._last_delivered_w = 0.0
        self._period_s = sample_period_s
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

    def start_worker(self) -> None:
        with self._lock:
            if self._worker is not None:
                return
            self._worker = threading.Thread(
                target=self._run, name="SocketSimulator", daemon=True
            )
            self._worker.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=2)
        with self._lock:
            self._controller.stop()
            self._last_delivered_w = 0.0

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.step()
            self._stop_event.wait(self._period_s)

    def step(self) -> None:
        """Single sensor sample and controller iteration (also testable manually)."""
        with self._lock:
            now = self._clock()
            dt = max(0.0, now - self._last_step_at)
            # Integration of PREVIOUS confirmed delivered load over elapsed dt.
            self._energy_wh += self._last_delivered_w * dt / 3600.0
            self._last_step_at = now

            self._controller.tick()
            if self._controller.status.state == SocketState.RUNNING:
                # Virtual power meter measures power on an energized output.
                self._controller.receive_measurement(self._requested_power_w)

            if self._controller.status.state == SocketState.RUNNING:
                self._last_delivered_w = self._requested_power_w
            else:
                self._last_delivered_w = 0.0

    def set_limit(self, value: int) -> None:
        with self._lock:
            current = self._controller.status
            self._controller.configure(value, current.duration_s)
            self._last_delivered_w = 0.0

    def set_duration(self, value: int) -> None:
        with self._lock:
            current = self._controller.status
            self._controller.configure(current.selected_power_w, value)
            self._last_delivered_w = 0.0

    def set_requested_power(self, value: float) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
            or not 0 <= value <= 2000
        ):
            raise ValueError("Snaga potrošača mora biti od 0 do 2000 W.")
        with self._lock:
            self._requested_power_w = float(value)
            # Sample immediately if running, just as a changed sensor reading.
            self.step()

    def start(self) -> None:
        with self._lock:
            self.step()
            self._controller.start()
            self._energy_wh = 0.0
            self._last_step_at = self._clock()
            self._last_delivered_w = 0.0
            self.step()  # first measurement immediately after energizing

    def stop(self) -> None:
        with self._lock:
            self.step()
            self._controller.stop()
            self._last_delivered_w = 0.0

    def reset(self) -> None:
        with self._lock:
            self.step()
            self._controller.reset()
            self._last_delivered_w = 0.0

    def state(self) -> dict:
        with self._lock:
            self.step()
            state = self._controller.status
            return {
                "state": state.state.value,
                "limit_w": state.selected_power_w,
                "allowed_powers_w": list(CONFIG.allowed_powers_w),
                "duration_s": state.duration_s,
                "remaining_s": round(state.remaining_s, 1),
                "requested_power_w": self._requested_power_w,
                "measured_power_w": state.measured_power_w,
                "delivered_power_w": self._last_delivered_w,
                "voltage_v": CONFIG.nominal_voltage_v,
                "current_a": round(self._last_delivered_w / CONFIG.nominal_voltage_v, 3),
                "energy_wh": round(self._energy_wh, 5),
                "output_enabled": state.output_enabled,
                "error_led_on": state.error_led_on,
                "message": state.error_message,
            }
