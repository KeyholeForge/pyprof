# solutions/ — mapowanie moduł → ćwiczenia

Ten katalog zawiera KOMPLETNE, DZIAŁAJĄCE wersje kodu, którego szkielet (z
`TODO`) uczeń dostaje w `app/`. Jedyny moduł ze szkieletem to
`app/profiling.py` — reszta `app/` (images.py, fetch.py, reports.py,
storage.py, main.py) działa od startu i NIE jest tu duplikowana jako
kumulatywne wersje; `*_fragmenty.py` pokazują tylko fragmenty do
wprowadzenia w ramach konkretnego ćwiczenia (naprawa wady albo — w
przypadku ćwiczenia 09 — świadome wprowadzenie i naprawa).

## app/profiling.py (warstwa-temat) — kumulatywne wersje

| Plik                            | Odblokowuje                                   | Ćwiczenie |
|----------------------------------|------------------------------------------------|-----------|
| `ex01_profiling.py`             | `init_profiling()` (pyroscope.configure; parametr `wall` przyjęty i na razie ignorowany) | 01 |
| `ex04_profiling.py`             | + `tag_wrapper()` (tagowanie per-endpoint)     | 04        |
| `ex07_profiling.py`             | + `start_memory_tracking()`/`get_memory_snapshot()` (tracemalloc) | 07 |
| `ex11_profiling.py`             | + tryb wall w `init_profiling` (`oncpu=not wall`, `gil_only=not wall`, tag `tryb`) | 11 |
| `exFINAL_profiling.py`          | wszystko naraz (identyczne z ex11)             | 16 / finał|

Użycie: `cp solutions/exNN_profiling.py app/profiling.py`, restart uvicorna.
Każdy kolejny plik jest nadzbiorem poprzedniego — funkcje z przyszłych
ćwiczeń wciąż mają `TODO`/`NotImplementedError`, więc kopiowanie np.
`ex04_profiling.py` daje dokładnie taki stan wiedzy, jaki uczeń powinien mieć
po ćwiczeniu 04, nie więcej.

Tryb próbkowania (cpu albo wall-clock) wybiera się **raz, przy starcie
procesu**: `PYROSCOPE_WALL=1 uvicorn app.main:app --host 127.0.0.1 --port 8040`.
W `pyroscope-io` 1.4.0 ponowne `pyroscope.configure()`, gdy agent działa, jest
odrzucane i nie zmienia ani trybu, ani tagów — dlatego nie ma przełącznika
w locie ani endpointu `/debug/profiling/mode`.

Sygnatura `tag_wrapper`: `pyroscope.tag_wrapper(tags: dict)` — context manager
przyjmujący JEDEN argument, słownik tagów. Ustawia tagi na **wątku**, więc w
handlerach `async def` (wspólny wątek pętli) tagi współbieżnych żądań się
mieszają (ćwiczenie 11, `11a`). Nasz `profiling.tag_wrapper` ma identyczną
sygnaturę i po prostu deleguje do biblioteki, żeby `app/main.py` miało stabilne API.

## Fragmenty i skrypty (naprawy wad, demonstracje)

| Plik                        | Co robi                                                | Ćwiczenie |
|------------------------------|---------------------------------------------------------|-----------|
| `profile_sepia.py`          | skrypt cProfile dla `_sepia_naive` (zapis `profiles/ex03_sepia.prof`) | 03 |
| `filters_fragmenty.py`      | W2 (CPU) — sepia przez `Image.convert(matrix=...)` zamiast pętli Pythona | 05 |
| `images_fragmenty.py`       | W1 (pamięć) — cache miniatur jako LRU (`OrderedDict`, limit 200) | 08 |
| `pipeline_fragmenty.py`     | W1b (prawdziwy wyciek) — A: graf współdzielony (główna), B: `unsubscribe` w `finally`, C: `WeakEventBus`; skrypt „kto trzyma” (`gc.get_referrers`) | 09 |
| `reports_fragmenty.py`      | W7 — wersje `+=` i `join` raportu (+ wyniki pomiaru; różnica w serwisie pomijalna) | 09 (★ Bonus B) |
| `gil_demo.py`               | demonstracja GIL: `sequential` / `threads N` / `processes N` (stała praca) | 10 |
| `fetch_fragmenty.py`        | W3a+W3b (TCP) — współdzielony `httpx.AsyncClient` (`fetch_one(client, url)`) + `asyncio.gather` | 12-13 |
| `storage_fragmenty.py`      | W4 (dysk) — bufor + jeden zapis/fsync zamiast fsync po każdym chunku | 14 |

Te pliki NIE są przeznaczone do podmiany 1:1 całego modułu (jak
`exNN_profiling.py`) — to fragmenty/funkcje do ręcznego przeniesienia, bo
dotykają pojedynczych funkcji w większych plikach (czasem dwóch plików
naraz, jak `fetch_fragmenty.py`, który zmienia i `main.py`, i `fetch.py`).

## Wady w kursie (rejestr — pełny opis i pomiary w `.kurs-build-state.md`)

Wszyte od startu w `app/`:
- **W1** (pamięć, ćw. 07-08): `THUMBNAIL_CACHE` w `app/images.py` — globalny
  dict bez evikcji → `images_fragmenty.py`.
- **W1b** (pamięć — prawdziwy wyciek, ćw. 09): `FilterPipeline` budowany w
  `images.apply_pipeline` przy każdym żądaniu i rejestrowany w globalnej szynie
  `pipeline.EVENTS` (`app/pipeline.py`) → `pipeline_fragmenty.py`. Endpoint
  `GET /images/{id}/pipeline/{preset}`, liczniki w `GET /debug/objects`, ruch
  `loadgen.py --scenario pipeline` (opcja `--requests N`).
- **W2** (CPU, ćw. 03/05/06): `_sepia_naive` w `app/images.py` → `filters_fragmenty.py`.
- **W3** (TCP, ćw. 12-13): `app/fetch.py` (klient per żądanie, fan-out w pętli) →
  `fetch_fragmenty.py`.
- **W4** (dysk, ćw. 14; spięcie z ćw. 11): `app/storage.py` → `storage_fragmenty.py`.

Wprowadzane instrukcją / demonstracje:
- **W5** (GIL, ćw. 10): `gil_demo.py` — wątki dla CPU-bound zamiast procesów;
  demonstracja standalone, bez zmian w `app/`.
- **W6** (sync-w-async, ćw. 11): blokujące wywołanie w `fetch_image` — wprowadzane i
  usuwane w treści ćwiczenia; w finale (ćw. 16) jako rzadka blokada.
- **W7** (konkatenacja stringów, ćw. 09 ★ Bonus B): w serwisie to mikrooptymalizacja
  **bez mierzalnego efektu** (lekcja o pomiarze przed optymalizacją); kod `app/reports.py`
  używa `join`. `reports_fragmenty.py` ma obie wersje i wyniki pomiaru.
- **W8** (regresja między wersjami, ćw. 15): cofnięcie naprawy W2 i tag `version`
  w treści ćwiczenia; brak osobnego pliku kodu.

Finał (ćw. 16): W1 + W2 + W3 (a+b) + W6 (rzadka blokada); W4 naprawione.
Klucz z liczbami: `ex16_odpowiedzi.md`. Pytania i odpowiedzi: `pytania_odpowiedzi.md`;
stopniowane podpowiedzi: `hints/`; mapa umiejętności i warianty odbiorcy: `todo.md`.
