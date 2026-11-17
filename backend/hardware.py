class SimulatedIO:
    output_enabled: bool = False
    error_led_on: bool = False

    def set_output(self, enabled: bool) -> None:
        self.output_enabled = enabled

    def set_error_led(self, enabled: bool) -> None:
        self.error_led_on = enabled