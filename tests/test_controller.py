
"""Automatski testovi upravljačke logike bez čekanja u stvarnom vremenu."""
import unittest

from backend.config import CONFIG
from backend.controller import (
    MEASUREMENT_ERROR_MESSAGE,
    MEASUREMENT_TIMEOUT_MESSAGE,
    OVERLOAD_MESSAGE,
    SmartSocketController,
    SocketState,
)
from backend.hardware import SimulatedIO


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestSmartSocketController(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.io = SimulatedIO()
        self.socket = SmartSocketController(io=self.io, clock=self.clock)

    def start_socket(self, power: int = 300, duration: int = 10) -> None:
        self.socket.configure(power, duration)
        self.socket.start()

    def test_01_safe_initial_state(self):
        self.assertEqual(self.socket.status.state, SocketState.IDLE)
        self.assertFalse(self.io.output_enabled)
        self.assertFalse(self.io.error_led_on)

    def test_02_allowed_powers(self):
        for power in (300, 600, 900):
            with self.subTest(power=power):
                self.socket.configure(power, 10)
                self.assertEqual(self.socket.status.selected_power_w, power)

    def test_03_reject_1000w(self):
        with self.assertRaises(ValueError):
            self.socket.configure(1000, 10)

    def test_04_reject_negative_power(self):
        with self.assertRaises(ValueError):
            self.socket.configure(-300, 10)

    def test_05_reject_zero_duration(self):
        with self.assertRaises(ValueError):
            self.socket.configure(300, 0)

    def test_06_reject_duration_over_max(self):
        with self.assertRaises(ValueError):
            self.socket.configure(300, CONFIG.max_duration_s + 1)

    def test_07_start_enables_output(self):
        self.start_socket()
        self.assertEqual(self.socket.status.state, SocketState.RUNNING)
        self.assertTrue(self.io.output_enabled)

    def test_08_start_twice_is_rejected(self):
        self.start_socket()
        with self.assertRaises(RuntimeError):
            self.socket.start()

    def test_09_measurement_below_limit(self):
        self.start_socket()
        self.socket.receive_measurement(200)
        self.assertEqual(self.socket.status.state, SocketState.RUNNING)
        self.assertTrue(self.io.output_enabled)

    def test_10_measurement_equal_to_limit(self):
        self.start_socket()
        self.socket.receive_measurement(300)
        self.assertEqual(self.socket.status.state, SocketState.RUNNING)

    def test_11_overload_trips_and_disconnects(self):
        self.start_socket()
        self.socket.receive_measurement(450)
        self.assertEqual(self.socket.status.state, SocketState.TRIPPED)
        self.assertFalse(self.io.output_enabled)
        self.assertTrue(self.io.error_led_on)
        self.assertEqual(self.socket.status.error_message, OVERLOAD_MESSAGE)

    def test_12_zero_power_is_valid(self):
        self.start_socket()
        self.socket.receive_measurement(0)
        self.assertEqual(self.socket.status.state, SocketState.RUNNING)

    def test_13_nan_measurement_trips(self):
        self.start_socket()
        self.socket.receive_measurement(float("nan"))
        self.assertEqual(self.socket.status.state, SocketState.TRIPPED)
        self.assertEqual(self.socket.status.error_message, MEASUREMENT_ERROR_MESSAGE)

    def test_14_negative_measurement_trips(self):
        self.start_socket()
        self.socket.receive_measurement(-10)
        self.assertEqual(self.socket.status.state, SocketState.TRIPPED)

    def test_15_no_measurement_trips_after_timeout(self):
        self.start_socket()
        self.clock.advance(CONFIG.measurement_timeout_s + 0.01)
        self.socket.tick()
        self.assertEqual(self.socket.status.state, SocketState.TRIPPED)
        self.assertFalse(self.io.output_enabled)
        self.assertEqual(self.socket.status.error_message, MEASUREMENT_TIMEOUT_MESSAGE)

    def test_16_timer_finishes(self):
        self.start_socket(duration=5)
        for _ in range(10):
            self.socket.receive_measurement(200)
            self.clock.advance(0.5)
            self.socket.tick()
        self.assertEqual(self.socket.status.state, SocketState.FINISHED)
        self.assertFalse(self.io.output_enabled)
        self.assertFalse(self.io.error_led_on)

    def test_17_stop_does_not_clear_trip(self):
        self.start_socket()
        self.socket.receive_measurement(400)
        self.socket.stop()
        self.assertEqual(self.socket.status.state, SocketState.TRIPPED)
        self.assertTrue(self.io.error_led_on)
        self.assertFalse(self.io.output_enabled)

    def test_18_reset_clears_trip_without_starting(self):
        self.start_socket()
        self.socket.receive_measurement(450)
        self.socket.reset()
        self.assertEqual(self.socket.status.state, SocketState.IDLE)
        self.assertFalse(self.io.error_led_on)
        self.assertFalse(self.io.output_enabled)

    def test_19_manual_stop(self):
        self.start_socket()
        self.socket.stop()
        self.assertEqual(self.socket.status.state, SocketState.IDLE)
        self.assertFalse(self.io.output_enabled)

    def test_20_fresh_measurements_keep_running(self):
        self.start_socket(duration=10)
        for _ in range(9):
            self.clock.advance(0.5)
            self.socket.receive_measurement(150)
            self.socket.tick()
        self.assertEqual(self.socket.status.state, SocketState.RUNNING)

    def test_21_configuration_during_running_is_rejected(self):
        self.start_socket()
        with self.assertRaises(RuntimeError):
            self.socket.configure(900, 10)

    def test_22_configuration_after_finished(self):
        self.start_socket(duration=1)
        self.clock.advance(1)
        self.socket.tick()
        self.socket.configure(900, 20)
        self.assertEqual(self.socket.status.state, SocketState.IDLE)
        self.assertEqual(self.socket.status.selected_power_w, 900)

    def test_23_reset_during_running_is_rejected(self):
        self.start_socket()
        with self.assertRaises(RuntimeError):
            self.socket.reset()

    def test_24_a_late_measurement_does_not_clear_timeout(self):
        self.start_socket()
        self.clock.advance(CONFIG.measurement_timeout_s + 0.1)
        self.socket.receive_measurement(100)
        self.assertEqual(self.socket.status.state, SocketState.TRIPPED)

    def test_25_external_code_cannot_modify_status(self):
        self.start_socket()
        snapshot = self.socket.status
        snapshot.state = SocketState.IDLE
        snapshot.output_enabled = False
        self.assertEqual(self.socket.status.state, SocketState.RUNNING)
        self.assertTrue(self.io.output_enabled)


if __name__ == "__main__":
    unittest.main()
