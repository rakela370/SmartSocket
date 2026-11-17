
# Pametna utičnica – Modul 2

Projekat iz predmeta **Implementacija automatskih sistema**.

## Specifikacija

- Nominalni napon: **220 V AC**.
- Izbor limita aktivne snage: **300, 600 ili 900 W**.
- Izbor trajanja rada: 1–86400 s (početna pretpostavka).
- Automatski prekid napajanja kada mjerenje premaši limit.
- Crvena LED i poruka pri prekoračenju ili neispravnom/nedostupnom mjerenju.
- Zaštitno stanje TRIPPED ostaje aktivno do RESET komande.
- Potpuno offline upravljačka logika.

## Arhitektura

- `backend/config.py` – fiksni projektni parametri.
- `backend/hardware.py` – simulacija kontaktora i signalne LED.
- `backend/controller.py` – automat stanja, zaštita i tajmer.
- `backend/main.py` – terminalski scenariji.
- `tests/test_controller.py` – automatizovana provjera.

U stvarnom uređaju potrebni su ESP32 firmware, fizički mjerač snage,
izolovano upravljanje kontaktorom, električna zaštita i ispitivanje. Python
simulacija **nije** direktno upravljanje mrežnim naponom.

## Pokretanje

Iz korijenskog foldera projekta:

```powershell
python -m unittest discover -s tests -v
python -m backend.main
```

Pojedinačni scenariji:

```powershell
python -m backend.main --scenario overload
python -m backend.main --scenario timer
python -m backend.main --scenario watchdog
python -m backend.main --scenario stop
python -m backend.main --scenario custom --limit 900 --duration 3 --load 850
python -m backend.main --scenario custom --limit 300 --duration 5 --load 400
```

## Stanja

- `IDLE` – izlaz isključen, čeka korisnika.
- `RUNNING` – izlaz uključen, vrši se mjerenje i odbrojavanje.
- `TRIPPED` – izlaz isključen zbog prekoračenja ili greške mjerenja; LED ON.
- `FINISHED` – izlaz isključen zbog isteka trajanja.

## Ograničenje Modula 2

Model pretpostavlja da `tick()` radi periodično i da je izmjerena snaga
pravovremena i tačna. Prag nedostupnosti mjerenja od 1 s je početna
simulaciona vrijednost, a ne validiran bezbjednosni parametar stvarne
utičnice. U fizičkom uređaju detekcija greške zavisi od odziva senzora,
firmware-a, drajvera i kontaktora, a sam uređaj zahtijeva zasebnu zaštitu.
