
import unittest

from backend.controller import (
    SmartSocketController,
    SocketState
)


class TestSmartSocket(unittest.TestCase):

    def test_allowed_powers(self):
        for power in (300, 600, 900):
            with self.subTest(power=power):
                socket = SmartSocketController()
                socket.configure(power, 60)
                self.assertEqual(
                    socket.status.selected_power, power
                )

    def test_invalid_power(self):
        socket = SmartSocketController()

        with self.assertRaises(ValueError):
            socket.configure(1000, 60)

    def test_normal_operation(self):
        socket = SmartSocketController()
        socket.configure(300, 60)
        socket.start()
        socket.update(200, 1)

        self.assertEqual(
            socket.status.state, SocketState.RUNNING
        )
        self.assertTrue(socket.status.output_enabled)

    def test_overload(self):
        socket = SmartSocketController()
        socket.configure(300, 60)
        socket.start()
        socket.update(450, 1)

        self.assertEqual(
            socket.status.state, SocketState.TRIPPED
        )
        self.assertFalse(socket.status.output_enabled)

    def test_timer_expiration(self):
        socket = SmartSocketController()
        socket.configure(600, 5)
        socket.start()
        socket.update(400, 5)

        self.assertEqual(
            socket.status.state, SocketState.FINISHED
        )
        self.assertFalse(socket.status.output_enabled)

    def test_invalid_measurement(self):
        socket = SmartSocketController()
        socket.configure(900, 60)
        socket.start()
        socket.update(float("nan"), 1)

        self.assertEqual(
            socket.status.state, SocketState.TRIPPED
        )
        self.assertFalse(socket.status.output_enabled)

    def test_no_restart_after_trip(self):
        socket = SmartSocketController()
        socket.configure(300, 60)
        socket.start()
        socket.update(500, 1)

        with self.assertRaises(RuntimeError):
            socket.start()


if __name__ == "__main__":
    unittest.main()
