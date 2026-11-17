"""Tests for revised Module 3: two tabs, manual load, localhost API."""
import http.client
from http.server import ThreadingHTTPServer
import json
import threading
import unittest

from backend.simulation_service import SimulationService
from backend.web_server import make_handler


class FakeClock:
    def __init__(self):
        self.value = 10.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class TestSimulationService(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.service = SimulationService(clock=self.clock)

    def test_initial_state_is_off_and_unloaded(self):
        state = self.service.state()
        self.assertEqual(state["state"], "IDLE")
        self.assertEqual(state["requested_power_w"], 0)
        self.assertFalse(state["output_enabled"])

    def test_250_w_below_300_w_remains_on(self):
        self.service.set_limit(300)
        self.service.set_requested_power(250)
        self.service.start()
        state = self.service.state()
        self.assertEqual(state["state"], "RUNNING")
        self.assertEqual(state["delivered_power_w"], 250)
        self.assertFalse(state["error_led_on"])

    def test_setting_load_while_idle_does_not_trip(self):
        self.service.set_limit(300)
        self.service.set_requested_power(2000)
        state = self.service.state()
        self.assertEqual(state["state"], "IDLE")
        self.assertEqual(state["delivered_power_w"], 0)

    def test_750_w_at_600_w_trips(self):
        self.service.set_limit(600)
        self.service.set_requested_power(750)
        self.service.start()
        state = self.service.state()
        self.assertEqual(state["state"], "TRIPPED")
        self.assertFalse(state["output_enabled"])
        self.assertTrue(state["error_led_on"])
        self.assertEqual(state["delivered_power_w"], 0)
        self.assertEqual(state["measured_power_w"], 750)

    def test_increase_during_operation_causes_trip(self):
        self.service.set_limit(300)
        self.service.set_requested_power(200)
        self.service.start()
        self.service.set_requested_power(450)
        self.assertEqual(self.service.state()["state"], "TRIPPED")

    def test_stop_does_not_clear_error(self):
        self.service.set_requested_power(1500)
        self.service.start()
        self.service.stop()
        self.assertEqual(self.service.state()["state"], "TRIPPED")

    def test_reset_comes_back_to_idle_without_power(self):
        self.service.set_requested_power(1000)
        self.service.start()
        self.service.reset()
        state = self.service.state()
        self.assertEqual(state["state"], "IDLE")
        self.assertFalse(state["error_led_on"])
        self.assertFalse(state["output_enabled"])

    def test_zero_w_load_is_accepted(self):
        self.service.set_requested_power(0)
        self.service.start()
        self.assertEqual(self.service.state()["state"], "RUNNING")
        self.assertEqual(self.service.state()["current_a"], 0)

    def test_energy_and_timer(self):
        self.service.set_limit(600)
        self.service.set_duration(2)
        self.service.set_requested_power(360)
        self.service.start()
        self.clock.advance(0.5)
        self.service.state()
        self.clock.advance(0.5)
        state = self.service.state()
        self.assertEqual(state["state"], "RUNNING")
        self.assertAlmostEqual(state["energy_wh"], 0.1, places=5)
        self.clock.advance(0.5)
        self.service.state()
        self.clock.advance(0.5)
        state = self.service.state()
        self.assertEqual(state["state"], "FINISHED")
        self.assertFalse(state["output_enabled"])
        self.assertAlmostEqual(state["energy_wh"], 0.2, places=5)

    def test_invalid_load_rejected(self):
        for value in (-1, 2001, float("nan"), True, "200"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.service.set_requested_power(value)

    def test_only_three_limits(self):
        with self.assertRaises(ValueError):
            self.service.set_limit(1000)

    def test_limit_locked_during_run(self):
        self.service.start()
        with self.assertRaises(RuntimeError):
            self.service.set_limit(900)

    def test_start_locked_after_trip(self):
        self.service.set_requested_power(2000)
        self.service.start()
        with self.assertRaises(RuntimeError):
            self.service.start()

    def test_current_equals_power_over_220_for_resistive_model(self):
        self.service.set_limit(900)
        self.service.set_requested_power(660)
        self.service.start()
        self.assertAlmostEqual(self.service.state()["current_a"], 3.0)


class TestLocalAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = SimulationService()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.service))
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.service.shutdown()

    def request(self, method, path, payload=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        if method == "POST":
            body = json.dumps(payload or {})
            headers = headers or {
                "Content-Type": "application/json", "X-Socket-UI": "1",
                "Origin": f"http://127.0.0.1:{self.port}",
            }
        else:
            body = None
            headers = headers or {}
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        data = response.read()
        status = response.status
        conn.close()
        return status, data

    def test_api_exposes_offline_state(self):
        status, body = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertIn("limit_w", json.loads(body))

    def test_html_has_two_tabs(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn('id="tab-socket"', text)
        self.assertIn('id="tab-load"', text)

    def test_cross_origin_mutation_denied(self):
        status, _ = self.request("POST", "/api/load", {"value": 700}, {
            "Content-Type": "application/json", "X-Socket-UI": "1",
            "Origin": "https://another-site.example",
        })
        self.assertEqual(status, 403)

    def test_invalid_limit_returns_friendly_error(self):
        status, body = self.request("POST", "/api/limit", {"value": 1000})
        self.assertEqual(status, 400)
        self.assertIn("300, 600 ili 900", body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
