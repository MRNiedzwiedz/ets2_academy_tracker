# Zweryfikowany format SII

Źródłem klucza jest dostarczony `ets2_academy_extract.py`; nie zmodyfikowano go.
ScsC: magic 0–3, MAC 4–35, IV 36–51, długość little endian uint32 52–55,
szyfrogram AES-256-CBC od 56. Padding PKCS#7, następnie zlib.
Dekoder sprawdza długość, wyrównanie, padding, pełny strumień zlib i rozmiar wyjścia.
Limit źródła i danych po dekompresji wynosi 64 MiB.

HMAC **nie jest weryfikowany**: prototyp nie podaje potwierdzonej konstrukcji
MAC ani klucza. Każdy import ScsC zapisuje jawne ostrzeżenie w diagnostyce/logu.
Poprawny padding i zlib nie są potwierdzeniem autentyczności pliku.

BSII wymaga zaufanego zewnętrznego dekodera. JSON `bsii_command` zawiera argumenty
wykonywalnego programu, z `{input}` i opcjonalnym `{output}`. Bez `{output}`
adapter odczytuje zmienioną kopię wejściową. Bez skonfigurowanego programu import
kończy się czytelnym błędem. Nie dołączono ani nie zweryfikowano dekodera BSII.

Parser używa tokenizacji i strukturalnego czytania obiektów i pól. Obsługuje
napisy, komentarze, tablice, nil, bool, liczby i wartości nawiasowe. Hex float
`&...`, tokeny i nieznane formy pozostają tekstem. Obiekt przechowuje także
surowe wartości. Parser nie wykonuje dyrektyw include ani kodu z pliku.

`academy_save_container.log` wskazuje `academy_log`; tablica `entries[n]`
określa kolejność zdarzeń. `scenario_start.link` jest kodem scenariusza,
`scenario_end.link` wskazuje `academy_scenario_result`. Nie analizujemy luźnych
wpisów poza dziennikiem ani samych wyników jako dodatkowych prób.

## Próbki dostarczone 21 listopada 2026

Po korekcie użytkownika źródłem testów jest `academy_book_states (2).sii` (6088 B).
Odszyfrowany tekst ma 61462 znaki, 48 zdarzeń, 23 obiekty wyników i 21 prób
w 9 scenariuszach. Dwa wyniki poza dziennikiem nie są dodatkowymi próbami.
Dostarczony `academy_book_states%20(2)_decoded.sii` służy do porównania treści.
CSV zawiera pierwszych 12 prób ze starszej wersji tej historii; adresy wyników
różnią się od obecnych i nie stanowią trwałych identyfikatorów.

Ranga `0` ani `nil` nie dowodzi sukcesu lub porażki. Wszystkie 21 zakończonych
prób ma `status=unknown`. `scenario_duration` pozostaje surowe. Różnica timestampów
startu/końca jest przechowywana osobno jako `elapsed_seconds`.
