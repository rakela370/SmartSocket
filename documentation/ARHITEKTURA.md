# Pametna utičnica – inženjerska arhitektura (radna verzija)

## Usvojeni zahtjevi

- Nominalno 220 V AC, jednofazno.
- Dozvoljeni limiti **300 W / 600 W / 900 W**, ne 1000 W.
- Korisnik bira limit i trajanje; izlaz je bez napajanja do START komande.
- Opterećenje koje pokušava da troši više od limita izaziva isključenje i crvenu signalizaciju.
- Uređaj radi autonomno **bez interneta, Wi-Fi-ja, aplikacije i cloud-a**.
- Za demonstraciju postoji isključivo lokalna računarska simulacija sa dva taba.

## Razdvajanje simulacije od stvarnog uređaja

**Simulacija u računaru:** korisnik na tabu „Utičnica“ bira limit i vrijeme;
na tabu „Potrošač“ bira zahtijevanu aktivnu snagu 0–2000 W. Python
`SimulationService` emulira mjerač i trenutno stanje potrošača, a postojeći
`SmartSocketController` odlučuje o uključenju i grešci. UI nikada ne postavlja
`output_enabled` direktno. Lokalni HTTP na `127.0.0.1` služi samo između
browsera i Python procesa na istom računaru, bez interneta.

**Stvarna utičnica:** lokalni HMI povezan serijskom vezom sa ESP32-S3;
ESP32-S3 pokreće *firmware* koji posjeduje nezavisan automat stanja;
poseban mjerni sklop mjeri napon, struju i **aktivnu snagu**;
upravljački izlaz preko odgovarajućeg izolovanog drajvera upravlja
kontaktima releja/kontaktora. Crvena LED signalizuje TRIPPED.

## Tok događaja – primjer 300 W / 450 W

1. Korisnik na HMI izabere 300 W i vrijeme; HMI po žičnoj vezi šalje
   komandu. Firmware provjerava da je 300 W dozvoljena vrijednost i čuva limit.
2. Na START, ako je uređaj spreman i mjerni lanac ispravan, kontroler
   daje komandu za zatvaranje izlaznih kontakata. Opterećenje dobija 220 V AC.
3. Potrošač pokušava da povuče 450 W. Mjerni sklop očitava strujne i
   naponske signale i iz njih procjenjuje aktivnu snagu.
4. Firmware poredi izmjerenu aktivnu snagu sa 300 W i otkriva prekoračenje.
5. Kontroler uklanja signal za uključivanje; odgovarajući relej/kontaktor
   otvara kontakte, LED postaje crvena, displej prikazuje grešku.
6. TRIPPED je zapamćen: izmjena opterećenja ili STOP ne uključuju
   izlaz automatski. RESET zahtijeva korisničku akciju, uz prethodno
   uklanjanje uzroka greške.

**Fizičko ograničenje:** mjerenje i isključenje nisu trenutni. Prekoračenje
može nakratko postojati do detekcije i otvaranja kontakata. Precizan odziv
mora biti projektovan i dokazan mjerenjima; simulacija nije dokaz brzine.

## Senzor, izolacija i dodatna električna zaštita

Razmotrićemo namjenski mjerni IC (npr. Analog Devices ADE7953) koji
omogućava mjerenje električnih parametara i signalizaciju prevelike
struje. Detekcija **aktivne snage** ostaje zadatak firmware-a na osnovu
mjerenja. Izbor mjernog elementa, kalibracija, galvanijska izolacija,
napajanje, PCB creepage/clearance, PE kontinuitet, zaštitni osigurači,
nadstrujna i kratkospojna zaštita i nazivna sposobnost kontakata zahtijevaju
posebnu tehničku verifikaciju. Nije dovoljno imati samo kontroler i relej.

Konačni popis komponenti, detaljne šeme, tolerancije, režimi kvara i
metodologija ispitivanja rade se u Modulu 5–6. Ovaj dokument **nije** šema
za neposredno priključivanje na mrežni napon.

## Softverski automat stanja

- IDLE: izlaz isključen, konfigurisanje dozvoljeno.
- RUNNING: izlaz uključen, mjerni i vremenski nadzor aktivan.
- TRIPPED: prekoračenje/gubitak mjerenja, izlaz isključen, LED crvena,
  samo eksplicitni RESET može obrisati zaštitno stanje.
- FINISHED: istek vremena, izlaz isključen, novi START tek poslije RESET.

## Matematički model (Modul 3)

Virtuelni potrošač je **otporni model** sa faktorom snage 1:

- P = U_RMS × I_RMS, uz U_RMS = 220 V.
- I = P / 220 V.
- E_Wh ≈ Σ(P_isporučeno,prethodni_uzorak × Δt) / 3600.

Tražena snaga od 0–2000 W nije isto što i stvarno isporučena snaga:
isključeni izlaz daje 0 W isporuke. Zaštita se ne pokreće samim unosom
zahtijevane snage kada je kontaktor otvoren; aktivira se nakon START i
mjerenja na energizovanom izlazu. Kasnije ćemo modelovati vrijeme odziva,
mjerenu snagu, kvarove i tolerancije detaljnije.
