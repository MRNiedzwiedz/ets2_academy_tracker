# ETS2 Academy Tracker

Lokalna aplikacja Windows 10/11 x64 do historii Driving Academy w ETS2.
PySide6, SQLite, watchdog, AES/zlib i raporty Excel. Pliki gry są tylko odczytywane.

## Uruchomienie

Gotowy plik po zbudowaniu: `dist/ETS2AcademyTracker.exe`. Możesz również kliknąć
`start.cmd`, który wybiera EXE lub lokalnego Pythona. Program nie potrzebuje sieci
podczas pracy. Pierwsza instalacja zależności wymaga pobrania pakietów.

Standardowa instalacja z Pythonem **3.12 x64**:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe main.py
```

W tym katalogu przygotowano także lokalny interpreter w `.tools/python`:

```powershell
.\.tools\python\python.exe main.py
.\.tools\python\python.exe -m pytest -q
```

## Pierwsze użycie

1. W zakładce **Użytkownicy** dodaj kursanta, potem jego profil ETS2.
2. Wskaż plik `academy_book_states.sii` lub katalog, który go zawiera. Lokalizacja
   zależy od profilu i Steam Cloud; nazwa folderu nie zastępuje imienia kursanta.
3. Wybierz profil i kliknij **Importuj profil**. Profile z flagą monitorowania `1`
   są automatycznie sprawdzane po uruchomieniu. Przycisk u góry zatrzymuje monitor.
4. Sprawdź **Scenariusze** i **Historię prób**. Filtry obejmują użytkownika, profil,
   scenariusz, status i daty startu (lub końca, gdy start nie istnieje).
5. W **Eksport** wybierz filtry i zapisz XLSX. Cztery arkusze powstają z bazy.

Rangi `0` i `nil` nie są automatycznie interpretowane jako zaliczenie/porażka.
Zakończone próby mają `unknown`; czas gry ma niepotwierdzoną jednostkę.
Kolumna czasu w sekundach oznacza wyłącznie różnicę timestampów start/koniec.

## Dane i konfiguracja

Domyślnie `%LOCALAPPDATA%/ETS2AcademyTracker`: `academy.db`, `config.json` po
zapisaniu ustawień oraz rotowane `tracker.log` (3 kopie po 2 MB).
Konfiguracja JSON jest opcjonalna; przykład w `config.example.json`.
Alternatywny plik: `python main.py --config C:/sciezka/config.json`.
Zmiana katalogu danych wymaga restartu, nie przenosi istniejącej bazy. Do kopii
zapasowej zamknij aplikację i skopiuj katalog danych. Nie usuwaj bazy, jeśli chcesz
zachować historię, której nie ma już w zapisach gry.

ScsC działa na kluczu zweryfikowanym z dostarczoną próbką. HMAC pozostaje
niezweryfikowany i jest jawnie raportowany. BSII wymaga konfiguracji zewnętrznego
dekodera: lista argumentów JSON z `{input}` i opcjonalnym `{output}`. Dopasuj ją
do interfejsu konkretnego narzędzia, np. dekodera modyfikującego plik w miejscu:

```json
["C:/tools/your-verified-decoder.exe", "{input}"]
```

Dekoder otrzymuje wyłącznie prywatną kopię, nigdy oryginalny plik gry.
Zewnętrzny dekoder BSII nie jest częścią dystrybucji ani testów referencyjnych.

## CLI i budowanie EXE

```powershell
python scripts/inspect_sii.py "academy_book_states (2).sii"
python scripts/import_once.py "academy_book_states (2).sii" --database data/demo.db --user Kursant --profile Test
python -m pytest -q
python -m PyInstaller --clean --noconfirm ETS2AcademyTracker.spec
```

Albo `powershell -File scripts/build.ps1`. Spec buduje pojedynczy EXE z GUI,
schematem SQLite i danymi stref czasowych. Sam EXE nie wymaga zainstalowanego Pythona.
Nie jest podpisany certyfikatem wydawcy. Nie dołączaj prywatnych zapisów gry do
publicznego repozytorium; pliki referencyjne są celowo w `.gitignore`.

Szczegóły: [architektura](docs/architecture.md), [format i ograniczenia](docs/sii_format.md),
[testowanie](docs/testing.md). Skrajnie identycznych zdarzeń po obcięciu dziennika
nie da się niezawodnie rozróżnić bez trwałych identyfikatorów od gry; ograniczenia
algorytmu tożsamości są opisane w architekturze.
