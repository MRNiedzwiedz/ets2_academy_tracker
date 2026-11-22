# Testowanie i wynik weryfikacji

Weryfikacja na Windows 11 x64, 21 listopada 2026, Python 3.12.10.
Pakiety użyte w środowisku są zapisane w `requirements-lock.txt`.

```powershell
.\.tools\python\python.exe -m pytest -q
.\.tools\python\python.exe scripts/inspect_sii.py "academy_book_states (2).sii"
.\.tools\python\python.exe -m PyInstaller --noconfirm ETS2AcademyTracker.spec
.\.tools\python\python.exe scripts/verify_release.py "academy_book_states (2).sii" --exe dist/ETS2AcademyTracker.exe
```

Ostatni przebieg: **42 testy zaliczone**. Zakres:

- rzeczywisty ScsC, zgodność odszyfrowanego SII i pierwszych 12 wierszy CSV;
- syntetyczny AES, PKCS#7, uszkodzone nagłówki, padding, rozmiar i zlib;
- adapter BSII na kontrolowanym programie testowym, także wewnątrz ScsC;
- parser struktury, tablice, nil, zachowanie surowych wartości, błędy składni;
- referencje wyników, wiele prób, koniec/start osierocony, niejednoznaczny restart;
- wiele profili, kolizje timestampów, przemianowanie adresów `_nameless`;
- idempotencja, ponowne otwarcie SQLite, dopisany koniec, obcięta historia;
- późniejsze uzupełnienie startu i brakującego wyniku, audyt scalenia obserwacji;
- sprzeczna kolejność dziennika i wymuszony błąd transakcji: rollback + retry;
- monitorowanie rzeczywistego katalogu, przerwany zapis i atomowa podmiana pliku;
- PySide6: 6 zakładek, import w tle, odświeżenie tabel, bezpieczne zatrzymanie;
- XLSX: cztery arkusze, puste dane, filtry, daty, brak duplikatów i formuł z nazw;
- zapis/odczyt i walidacja konfiguracji.

Testy GUI używają `QT_QPA_PLATFORM=offscreen`. Testy realnej próbki są pomijane
wyłącznie wtedy, gdy prywatne pliki nie są dostępne po sklonowaniu repozytorium.
Lokalnie wszystkie próbki są obecne; nie było pominiętych testów.

## Rzeczywista próbka i artefakty

`academy_book_states (2).sii`: SHA256
`ff61cb023f989c9acdf447014eaf4bc9d2281baa3a99b7b426d1b3738f20944f`.

Zaimportowano 48 zdarzeń i 21 prób w 9 scenariuszach. Wszystkie zakończone próby
mają `unknown`. Kolejny import nie tworzy nowych prób. Odszyfrowany tekst jest
zgodny z dostarczonym SII po normalizacji CRLF/LF. CSV odpowiada pierwszym 12
próbom pod względem scenariusza, punktów, rangi, surowego czasu i elapsed_seconds.
Hash źródła jest identyczny przed importem, po imporcie i po eksporcie.

Lokalne pliki do przeglądu (pomijane przez Git):

- `dist/ETS2AcademyTracker.exe` — pojedynczy plik aplikacji Windows;
- `data/verification/Academy-przyklad.xlsx` — raport rzeczywistej próbki;
- `data/verification/result.json` — wynik importu i kontroli EXE;
- `data/verification/dashboard.png`, `history.png` — podgląd GUI;
- `data/verification/academy.db` — osobna baza testowa, niezależna od danych produkcyjnych.

Zbudowany EXE uruchomiono z osobnym configiem i `--smoke-test` (GUI w trybie
offscreen, monitor, automatyczne zamknięcie po 1,5 s); kod wyjścia 0.
Kontrola XLSX polega na ponownym odczycie przez openpyxl, nie na automatyzacji
zainstalowanego Microsoft Excel. Nie przeprowadzono sesji z uruchomioną grą ani
testu na oddzielnym komputerze z Windows 10. Adapter BSII przetestowano na kopii
z kontrolowanym programem, nie na rzeczywistym pliku BSII i zewnętrznym dekoderze.

HMAC pozostaje niezweryfikowany. Brak potwierdzonych reguł rang i jednostki czasu
jest celowym ograniczeniem opisanym w `sii_format.md` i `architecture.md`.
