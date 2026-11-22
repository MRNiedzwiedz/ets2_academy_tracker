# Architektura

Aplikacja działa lokalnie na Pythonie 3.12 i Windows x64. Nie korzysta z serwera
ani sieci w czasie pracy. `main.py` wczytuje JSON, ustawia rotację logów i otwiera
PySide6. Dane domyślne: `%LOCALAPPDATA%/ETS2AcademyTracker`.

Przepływ: watchdog / skan okresowy → kolejka profili → stabilny snapshot RAM →
SHA256 → Decoder → parser struktury SII → rozwiązanie referencji dziennika →
SQLite → GUI / raport XLSX. Oryginalne zapisy są otwierane tylko jako `rb`.
Adapter BSII przekazuje zewnętrznemu programowi wyłącznie kopię w katalogu tymczasowym.

## Moduły i wątki

- `academy`: dekoder, scanner/parser, modele i dopasowanie prób bez zależności od GUI.
- `database`: schema v2, migracje, repozytorium; FK, WAL, transakcje i indeksy.
- `monitoring`: odczyt, importer i monitor. Jeden QThread obsługuje kolejkę monitorowania.
- `ui`: sygnały Qt; import ręczny i eksport używają QThreadPool. Każda operacja
  otwiera własne połączenie SQLite. GUI odczytuje niewielkie zestawienia z bazy.
- `reports`: spójna transakcja odczytowa, cztery arkusze, zapis tymczasowy + replace.

Przy zamknięciu monitor dostaje sygnał zatrzymania; okno czeka na zakończenie prac.
Nie zabija wątku w środku transakcji. Zewnętrzny dekoder ma timeout 30 s.

## Tożsamość, historia i atomowość

SHA256 identyfikuje snapshot osobno dla każdego profilu. Zdarzenia mają podpis
semantyczny: typ, timestamp, oryginalne pola oraz rozwiązany wynik wraz z celami.
Lokalne adresy `_nameless.*` są normalizowane. Kolejne identyczne wystąpienia w
jednym dzienniku mają osobny numer, więc ten sam timestamp i wynik nie sklejają
dwóch prób. UNIQUE obejmuje zawsze profil. Zmiana samych adresów nie dubluje danych.

`snapshot_events` zapisuje dokładną kolejność i członkostwo każdego snapshotu.
Historia scala ograniczenia kolejności z zaobserwowanych dzienników (sortowanie
topologiczne); nie sortuje zdarzeń według czasu systemowego ani według adresów.
Sprzeczne ograniczenia powodują bezpieczne wycofanie importu. Niezależne fragmenty
bez wspólnych zdarzeń zachowują kolejność pierwszej obserwacji.

Start jest tożsamością logiczną próby. Dopisany koniec aktualizuje ten sam rekord.
Koniec bez startu tworzy próbę osieroconą; późniejszy nakładający się snapshot może
ją uzupełnić. Numery prób są przydzielane przy pierwszym imporcie, osobno dla
profilu i scenariusza; nie zmieniają się po wczytaniu starszego fragmentu historii.
`source_snapshot_id` wskazuje pierwszą obserwację próby. Zniknięcie wpisu z gry
nie usuwa historii. GUI pokazuje osobno obecność w ostatnim poprawnym snapshotcie.

Jednoznacznie rozwiązany później brakujący wynik uzupełnia zdarzenie, zachowując
jego tożsamość. Jeżeli wcześniej zapisano zarówno start, jak i osierocony koniec
tej samej próby, są scalane; oryginalna obserwacja zostaje w tabeli audytu
`attempt_reconciliations`. Samo zniknięcie zdarzenia nigdy nie powoduje scalania.

Snapshot, zdarzenia, relacje i próby zatwierdzane są jedną transakcją IMMEDIATE.
Status `processed` jest zapisany wewnątrz niej. Błąd wycofuje dane; osobna
transakcja zapisuje diagnostykę `failed`, którą można ponowić.

## Granice identyfikacji

SII nie dostarcza potwierdzonego trwałego identyfikatora każdej próby.
Gdy gra usunie część zdarzeń i zastąpi je semantycznie identycznymi zdarzeniami
z dokładnie tymi samymi sekundami, nie da się dowieść, czy są nowe. Algorytm
przyjmuje zgodność według numeru wystąpienia i zachowuje wszystkie wcześniej
zarejestrowane rekordy. Snapshot z identycznymi wystąpieniami dostaje ostrzeżenie.
Nie gwarantuje to odtworzenia niewidocznych prób między odczytami. Zmiana treści
wyniku zmienia podpis zdarzenia; może wymagać ręcznej analizy jako nowa obserwacja.

Wielokrotne starty tego samego scenariusza przed końcem są niejednoznaczne:
pozostają oddzielne rekordy `unknown/ambiguous`, a koniec jest osierocony.
Nie używamy FIFO do zgadywania restartu. `interrupted`, `failed`, `completed`
są dozwolone w schemacie, ale obecne dane nie uzasadniają automatycznego
przypisywania tych statusów. Sam start pozostaje `in_progress`.

GUI wczytuje tabele w całości; przy bardzo dużej historii warto rozszerzyć je o
paginację QAbstractTableModel. Obecna wersja jest przeznaczona do lokalnych historii.
