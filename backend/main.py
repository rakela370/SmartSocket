
from .controller import SmartSocketController


def show_status(controller):
    s = controller.status

    print(f"Stanje: {s.state.value}")
    print(f"Limit: {s.selected_power} W")
    print(f"Izmjerena snaga: {s.measured_power} W")
    print(f"Preostalo vrijeme: {s.remaining_seconds:.1f} s")
    print(f"Izlaz ukljucen: {s.output_enabled}")

    if s.error_message:
        print(f"GRESKA: {s.error_message}")

    print("-" * 45)


def main():
    socket = SmartSocketController()

    print("PAMETNA UTICNICA - MODUL 1")
    print("=" * 45)

    socket.configure(power=300, duration=10)
    socket.start()

    print("\n1. Pokretanje")
    show_status(socket)

    print("\n2. Potrosac 200 W")
    socket.update(measured_power=200, elapsed=2)
    show_status(socket)

    print("\n3. Potrosac 280 W")
    socket.update(measured_power=280, elapsed=2)
    show_status(socket)

    print("\n4. Potrosac 450 W - PREKORACENJE")
    socket.update(measured_power=450, elapsed=1)
    show_status(socket)

    print("\n5. Reset uredjaja")
    socket.reset()
    show_status(socket)


if __name__ == "__main__":
    main()
