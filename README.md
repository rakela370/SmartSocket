# Pametna utičnica – Modul 3 (novi interaktivni koncept)

Master predmet: **Implementacija automatskih sistema**.

## Specifikacija

- Nominalno 220 V AC; tri dozvoljene snage: **300 / 600 / 900 W**.
- Korisnik bira trajanje, START / STOP / RESET.
- Simulirani potrošač ručno zahtijeva od **0 do 2000 W**.
- Prekoračenje: `TRIPPED`, otvoren izlaz, crvena LED, poruka na displeju.
- Bez unaprijed pokrenutih demonstracionih scenarija.
- Sistem i svi podaci rade **offline**.

## Pokretanje

Potrebna je Python 3.11+ instalacija. Nema dodatnih paketa.

```powershell
python -m unittest discover -s tests -v
python -m backend.web_server
```

U browseru otvori **http://127.0.0.1:8765**.

Na tabu **Pametna utičnica** izaberi limit (300/600/900 W), trajanje
u sekundama i klikni UKLJUČI. Na tabu **Električni potrošač** klizačem
mijenjaj traženu snagu od 0 do 2000 W. Pri prekoračenju kontroler
isključuje izlaz, pali crvenu LED i prikazuje grešku. Nakon otklanjanja
uzroka klikni RESET pa UKLJUČI.

Terminal i dalje mogu poslužiti za staru demonstraciju Modula 2:

```powershell
python -m backend.main
```

## Struktura

- `backend/controller.py` – postojeći automat stanja iz Modula 2 (**ne mijenja se**).
- `backend/simulation_service.py` – virtuelni mjerni sklop i potrošač.
- `backend/web_server.py` – lokalni HTTP server samo na `127.0.0.1`.
- `frontend/index.html` – dva taba.
- `frontend/style.css` – izgled utičnice i uređaja.
- `frontend/app.js` – slanje korisničkih komandi i osvježavanje stanja.
- `tests/test_ui_service.py` – dodatni testovi.
- `documentation/ARHITEKTURA.md` – stvarni princip rada i ograničenja.

### Bez interneta

Browser i Python razmjenjuju podatke preko **loopback** adrese `127.0.0.1`
na istom računaru, a ne preko javnog interneta. Stvarna verzija uređaja
neće koristiti ovaj server: ESP32-S3 samostalno upravlja mjerenjem,
kontaktorom i lokalnim HMI-jem putem žične komunikacije.

## Ograničenja trenutne simulacije

- Opterećenje je za sada idealizovano, otporno: cos φ = 1.
- Simulacija detektuje prekoračenje u narednom softverskom očitavanju.
- Stvaran fizički prekidač, senzori, izolacija i reakcijsko vrijeme tek
  treba da budu projektovani, modelovani i ispitani.
- Prikaz ne predstavlja fizički bezbjedan uređaj spreman za mrežnu upotrebu.
