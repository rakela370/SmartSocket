
"""Terminalska demonstracija Modula 2 (bez interneta)."""
import argparse
import sys
import time

from .controller import SmartSocketController, SocketState


def print_status(controller: SmartSocketController) -> None:
    s = controller.status
    power = (
        "nema mjerenja"
        if s.measured_power_w is None
        else f"{s.measured_power_w:.0f} W"
    )
    print(
        f"Stanje={s.state.value:<8} | limit={s.selected_power_w:>3} W "
        f"| potrosnja={power:<14} | preostalo={s.remaining_s:>4.1f} s "
        f"| izlaz={'UKLJ' if s.output_enabled else 'ISKLJ'} "
        f"| crvena LED={'ON' if s.error_led_on else 'OFF'}"
    )
    if s.error_message:
        print("PORUKA:", s.error_message)


def run_scenario(
    title: str,
    limit_w: int,
    duration_s: int,
    load_w: float,
    mode: str = "normal",
) -> None:
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")
    controller = SmartSocketController()
    controller.configure(limit_w, duration_s)
    controller.start()
    print_status(controller)

    started = time.monotonic()
    next_print = started
    try:
        while controller.status.state == SocketState.RUNNING:
            elapsed = time.monotonic() - started
            controller.tick()

            if controller.status.state != SocketState.RUNNING:
                break

            if mode != "watchdog" or elapsed < 0.6:
                controller.receive_measurement(load_w)

            if mode == "manual_stop" and elapsed >= 1.0:
                controller.stop()

            if time.monotonic() >= next_print:
                print_status(controller)
                next_print += 0.5

            time.sleep(0.1)
    except KeyboardInterrupt:
        controller.stop()
        print("\nPrekinuto tastaturom - izlaz iskljucen.")

    print("KONACNO STANJE:")
    print_status(controller)

    if controller.status.state == SocketState.TRIPPED:
        controller.stop()
        print("Nakon STOP (greska i dalje postoji):")
        print_status(controller)
        controller.reset()
        print("Nakon RESET:")
        print_status(controller)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pametna uticnica - Modul 2")
    parser.add_argument(
        "--scenario",
        choices=["all", "overload", "timer", "watchdog", "stop", "custom"],
        default="all",
    )
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--load", type=float, default=200)
    args = parser.parse_args()

    # Validacija prije bilo kakvog prikaza: neispravan izbor ispisuje samo gresku.
    if args.scenario == "custom":
        try:
            SmartSocketController().configure(args.limit, args.duration)
        except (ValueError, RuntimeError) as exc:
            print(f"GRESKA: {exc}", file=sys.stderr)
            return 2

    print("PAMETNA UTICNICA - MODUL 2 | OFFLINE SIMULACIJA", flush=True)
    scenarios = {
        "overload": ("TEST 1 - PREKORACENJE", 300, 5, 450.0, "normal"),
        "timer": ("TEST 2 - ISTEK TAJMERA", 600, 2, 400.0, "normal"),
        "watchdog": ("TEST 3 - NESTANAK MJERENJA", 900, 5, 500.0, "watchdog"),
        "stop": ("TEST 4 - RUCNO ISKLJUCENJE", 900, 5, 200.0, "manual_stop"),
    }

    try:
        if args.scenario == "custom":
            run_scenario("KORISNICKI SCENARIO", args.limit, args.duration, args.load)
        elif args.scenario == "all":
            for scenario in scenarios.values():
                run_scenario(*scenario)
        else:
            run_scenario(*scenarios[args.scenario])
    except (ValueError, RuntimeError) as exc:
        print(f"GRESKA: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
