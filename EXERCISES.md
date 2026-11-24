# Spis ćwiczeń i czytanek

Kolejność jest progresywna — każde ćwiczenie buduje na poprzednim. Czytanki
teoretyczne (bez zadań) poprzedzają bloki, których dotyczą. Zacznij od
`exercises/00-teoria.md` — mapa pojęć całego kursu.

Czasy w tabeli to orientacyjny czas pracy **bez** czekania na start Pyroscope
(ok. 90 s przy pierwszym `docker compose up`) i na pojawienie się próbek po
ruchu (ok. 15–20 s). Cały kurs: ok. 10–11 godzin.

## Mapa umiejętności

Po ukończeniu kursu umiesz:
- uruchomić continuous profiling i czytać flamegraf, filtrować po tagach (ćw. 1, 4)
- podejrzeć żywy proces bez restartu (py-spy top/dump) (ćw. 2)
- sprofilować pojedynczą funkcję offline i porównać implementacje mikrobenchmarkiem (ćw. 3, 6)
- zdiagnozować i naprawić CPU-bound wadę (pętla Pythona → operacja natywna) (ćw. 5)
- znaleźć rosnący cache przez RSS, tracemalloc i memray, naprawić przez evikcję (ćw. 7-8)
- odróżnić prawdziwy wyciek od cache testem „to samo żądanie × N”, **znaleźć, kto trzyma referencję** (`gc.get_referrers`) i naprawić wyciek rejestru dwiema drogami: graf współdzielony vs wyrejestrowanie (ćw. 9); sprawdzić pomiarem, czy mikrooptymalizacja ma znaczenie (★ Bonus B w ćw. 9)
- wytłumaczyć i zademonstrować GIL — dlaczego wątki nie przyspieszają CPU-bound; **zdecydować „liczymy czy czekamy"** na podstawie czasu zegarowego i CPU (ćw. 10)
- wybrać tryb profilera (cpu / wall) przy starcie i zdiagnozować zamrożony event loop; rozpoznać trzy rodzaje blokady pętli (`sleep`, CPU, `fsync`) i **granice profilera próbkującego** — zawieszonej korutyny nie widać, tagi w `async def` się mieszają (ćw. 11, czytanka 11a)
- zdiagnozować wady sieciowe (nowy klient per żądanie, sekwencyjny fan-out) przez **liczbę połączeń, czas i hak `trace`**, a nie przez szeroką ramkę w profilu (ćw. 12-13)
- zdiagnozować wadę dyskową (nadmiarowy fsync): widoczną w wall, prawie niewidoczną w cpu; wiedzieć, czym macOS różni się od Linuksa (ćw. 14)
- porównać profile dwóch wersji aplikacji po tagu `version` i wykryć regresję wydajności (ćw. 15)
- zdiagnozować incydent z wieloma wadami naraz WYŁĄCZNIE przez narzędzia, dobierając narzędzie do rodzaju czekania i rozdzielając nakładające się objawy (ćw. 16)

<!-- Ta mapa POWSTAŁA PRZED listą ćwiczeń i wyznaczyła ich liczbę (METODYKA §5).
     Każde ćwiczenie buduje co najmniej jedną umiejętność z mapy. Pełny opis:
     solutions/todo.md -->

## Ćwiczenia

| #   | Plik                                  | Czas    | Co robisz |
|-----|----------------------------------------|---------|-----------|
| —   | `exercises/00-teoria.md`              | ~30 min | **Czytanka:** mapa pojęć profilowania (przeczytaj pierwsze) |
| 1   | `exercises/01.md`                     | ~30 min | Setup stacku + `init_profiling` + pierwszy flamegraf w Pyroscope |
| 2   | `exercises/02.md`                     | ~20 min | py-spy top/dump na żywym procesie, bez restartu |
| 3   | `exercises/03.md`                     | ~25 min | cProfile + snakeviz — profil offline jednej funkcji |
| 4   | `exercises/04.md`                     | ~35 min | `tag_wrapper` per-endpoint + czytanie flamegrafów + mini-incydent (koniec bloku A) |
| —   | `exercises/04a-cpu-od-srodka.md`      | ~15 min | **Czytanka:** koszt operacji w Pythonie, interpreter overhead (przed blokiem B) |
| 5   | `exercises/05.md`                     | ~30 min | Diagnoza i naprawa naiwnego filtra CPU (W2) |
| 6   | `exercises/06.md`                     | ~25 min | Mikrobenchmarki (`timeit`) + mini-incydent CPU (koniec bloku B) |
| —   | `exercises/06a-pamiec-cpythona.md`    | ~15 min | **Czytanka:** pamięć CPythona od środka; cache / wyciek / zaległa praca (przed blokiem C) |
| 7   | `exercises/07.md`                     | ~25 min | `tracemalloc` przez `/debug/memory` (narzut ×11) |
| 8   | `exercises/08.md`                     | ~40 min | RSS, tracemalloc i memray — diagnoza i naprawa cache miniatur bez limitu (W1) |
| 9   | `exercises/09.md`                     | ~60 min | Prawdziwy wyciek pamięci (W1b): graf per żądanie w globalnej szynie — test „to samo żądanie × N”, tracemalloc/memray, `gc.get_referrers`, dwie naprawy + mini-incydent cache czy wyciek (koniec bloku C); ★ W7 |
| —   | `exercises/09a-wspolbieznosc-gil-asyncio.md` | ~15 min | **Czytanka:** GIL, wątki, asyncio; „liczymy czy czekamy?" (przed blokiem D) |
| 10  | `exercises/10.md`                     | ~30 min | GIL — dlaczego wątki nie przyspieszają CPU-bound (`gil_demo.py`) |
| 11  | `exercises/11.md`                     | ~45 min | Tryb wall przy starcie, zamrożona pętla (W6): `sleep`, CPU, `fsync`; granice profilera + mini-incydent (koniec bloku D) |
| —   | `exercises/11a-io-sieci-dysku.md`     | ~20 min | **Czytanka:** I/O sieci i dysku + granice profilera próbkującego (przed blokiem E) |
| 12  | `exercises/12.md`                     | ~30 min | TCP — nowy klient httpx per request (W3a): liczba połączeń → współdzielony klient |
| 13  | `exercises/13.md`                     | ~30 min | Fan-out (W3b): czas i hak `trace` → `asyncio.gather`; kiedy równoległość nie pomaga |
| 14  | `exercises/14.md`                     | ~35 min | Dysk — fsync po każdym kawałku (W4), blokada pętli, `F_FULLFSYNC` + mini-incydent I/O (koniec bloku E) |
| 15  | `exercises/15.md`                     | ~35 min | Porównywanie profili po tagu `version` — regresja wydajności (W8) |
| 16  | `exercises/16.md`                     | ~75 min | Finałowy challenge — 4 wady naraz (dwie fazy), diagnoza WYŁĄCZNIE przez narzędzia |

Pojęcia w pigułce: `slownik.md`. Rozwiązania i podpowiedzi: katalog `solutions/`.
Weryfikacja „done": `python check.py exNN` (albo `python check.py --all`).

## Bloki tematyczne

- **A — Fundamenty** (ćw. 1-4): setup, narzędzia (Pyroscope/py-spy/cProfile),
  tagowanie, czytanie flamegrafów.
- **B — CPU** (ćw. 5-6): diagnoza i naprawa wady obliczeniowej, mikrobenchmarki.
- **C — Pamięć** (ćw. 7-9): tracemalloc, memray, cache bez limitu (W1), prawdziwy
  wyciek i „kto trzyma” (W1b).
- **D — Współbieżność** (ćw. 10-11): GIL, wątki vs procesy, „liczymy czy
  czekamy?", tryby cpu/wall, event loop i jego blokady, granice profilera.
- **E — Sieć/dysk** (ćw. 12-14): liczba połączeń TCP, fan-out, I/O dysku — i
  dobór narzędzia: profil czy stoper.
- **F — Finał** (ćw. 15-16): porównywanie profili po tagu `version`, finałowy
  challenge (diagnoza bez czytania kodu, nakładające się objawy).
