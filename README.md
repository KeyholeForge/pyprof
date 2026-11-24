# Kurs pyprof — profilowanie aplikacji Python na przykładzie pixelforge

> **Wersje językowe:** ta gałąź (`polish`) zawiera kurs po polsku.
> Wersja angielska jest na gałęzi [`main`](https://github.com/KeyholeForge/pyprof/tree/main).
> Aby przełączyć lokalne repozytorium na wersję angielską, użyj `git switch main`.

Praktyczny kurs „learn-by-doing": budujesz umiejętność profilowania aplikacji
FastAPI (`pixelforge` — serwis przetwarzania obrazów) i obserwujesz efekty w
Grafana Pyroscope. Uczysz się przez robienie — warstwa profilowania
(`app/profiling.py`) startuje nieukończona, a jej budowanie jest treścią
ćwiczeń 1, 4, 7 i 11. Reszta aplikacji (upload, miniatury, filtry, pobieranie
z URL, raporty) działa od pierwszego uruchomienia — Twoim zadaniem jest ją
DIAGNOZOWAĆ i NAPRAWIAĆ, nie pisać od zera. Instrukcje po polsku.

> **Kurs zweryfikowany 2026-11** na: macOS (Docker Desktop), Python 3.14.10
> (aplikacja uruchomiona też na 3.11), fastapi 0.162.0, starlette 1.10.0,
> uvicorn 0.54.0, httpx 0.28.1, pillow 13.0.0, memray 1.20.0, py-spy 0.4.2,
> pyroscope-io 1.4.0, snakeviz 2.2.2, grafana/pyroscope 2.4.2, nginx 1.30
> (origin), alpine 3.24. Liczby w ćwiczeniach pochodzą z jednej maszyny (14
> rdzeni) — to rzędy wielkości i stosunki, nie wartości do powtórzenia co do
> milisekundy.

Nacisk na teorię i jasne tłumaczenie pojęć — zacznij od `exercises/00-teoria.md`,
przed blokami czytaj `exercises/NNa-*.md`, definicje szukaj w `slownik.md`.

## Wymagania wstępne

- **Python 3.11–3.14, zwykły build z GIL.** Wersja `3.14t` (free-threaded) odpada:
  `pyroscope-io` się na niej nie instaluje. Sprawdź swój interpreter:
  `python3.14 -c "import sysconfig; print(sysconfig.get_config_var('Py_GIL_DISABLED'))"`
  ma wypisać `0` (albo `None`). Uwaga: `uv venv --python 3.14` potrafi wybrać build
  free-threaded — używaj `python3.14 -m venv` albo sprawdź wynik powyższym poleceniem.
- Podstawy Pythona (funkcje, klasy, `async`/`await` na poziomie
  „czytam i rozumiem", nie musisz umieć pisać zaawansowanego asyncio od zera).
- Umiejętność uruchomienia `docker compose up -d` i odczytania logów kontenera.
- Podstawy HTTP (co to GET/POST, kod statusu) — kurs NIE zakłada wcześniejszej
  wiedzy o profilowaniu, GIL-u, event loopie ani żadnym z narzędzi użytych w
  kursie (Pyroscope/py-spy/memray/cProfile) — tego uczy kurs od zera.
- Docker z min. ~1 GB wolnego RAM dla Pyroscope + origin. Brak kluczy API —
  kurs nie używa żadnego LLM ani usługi chmurowej.

## Architektura

```
   loadgen ──HTTP──▶  pixelforge (lokalnie, 127.0.0.1:8040)
                          │  warstwa-tematu: app/profiling.py (budowana w ćw. 1/4/7/11)
                          │  domena: upload/miniatury/filtry/fetch/raporty (app/*.py)
                          │  magazyn: data/uploads/ (runtime), data/corpus/ (korpus)
                          ├──telemetria (CPU albo wall-clock)──▶ Pyroscope (UI :4040)
                          └──HTTP (pobieranie obrazów)──▶ origin (nginx, Docker, :8041)
```

`origin` to nginx z HTTP/1.1 keep-alive i sztucznym opóźnieniem odpowiedzi
25 ms (`ORIGIN_DELAY_MS`, `tc netem`) — bez niego sieć lokalna jest zbyt szybka,
żeby wady z ćwiczeń 12–13 dały mierzalny sygnał. `GET /nginx_status` pokazuje
liczbę połączeń i żądań.

## Szybki start

0. Własny branch na pracę: `git switch -c moje-cwiczenia` — ćwiczenia
   modyfikują pliki aplikacji (`app/images.py`, `app/fetch.py`,
   `app/storage.py`, `app/reports.py`, `app/profiling.py`, `app/main.py`);
   czysty `main` to darmowy reset kursu, `git diff main` pokaże na końcu
   wszystko, co zbudowałeś/aś.
1. Środowisko (na macOS samo `python` często nie istnieje albo wskazuje
   systemowe 3.9 — podaj wersję jawnie):
   `python3.14 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. Korpus danych: `python scripts/gen_corpus.py` (musi istnieć PRZED startem
   `docker compose up`, bo serwis `origin` montuje `data/origin_images` jako
   wolumen tylko-do-odczytu).
3. Backend: `docker compose up -d --build --wait` → Pyroscope UI:
   `http://127.0.0.1:4040` (bez logowania). Pierwszy raz obrazy się budują, a
   Pyroscope potrzebuje ok. 60–90 s po starcie, zanim `/ready` przestanie
   zwracać 503 — `--wait` czeka na stan `healthy`.
4. Zmienne: `cp .env.example .env` (kurs nie ma sekretów — same lokalne adresy).
5. Zacznij od `exercises/00-teoria.md`, potem `exercises/01.md`.

## Uruchamianie aplikacji

```bash
python scripts/reset_uploads.py      # czyści data/uploads/ — rób to przed każdym pomiarem
uvicorn app.main:app --host 127.0.0.1 --port 8040
# w drugim terminalu:
python loadgen.py --duration 30 --concurrency 5 --scenario mixed
```

Tryb profilera (CPU albo wall-clock) wybierasz **przy starcie procesu**:
`PYROSCOPE_WALL=1 uvicorn app.main:app --host 127.0.0.1 --port 8040` (ćwiczenie
11). Zmiany trybu w działającej aplikacji nie ma — zmiana = restart.
`curl -s 127.0.0.1:8040/health` zwraca m.in. `pid` (przyda się py-spy i memray)
oraz stan profilowania (`"tryb": "cpu"|"wall"`). W terminalu uvicorna zobaczysz
też linię `Profiling aktywne (Pyroscope: …, tryb: …)`.

`GET /debug/objects` (bez zależności od `profiling.py`) zwraca liczniki żywych obiektów: `live_pipelines`, `event_subscribers`, `publish_us` — do ćwiczenia 9.

Dopóki `app/profiling.py` ma `TODO`, endpoint `/debug/memory` zwraca HTTP 501 z
podpowiedzią, w którym ćwiczeniu go odblokować — reszta aplikacji (upload/
miniatury/filtry/fetch/raporty) działa niezależnie od stanu profilowania.
Kryteria „done" sprawdzisz skryptem: `python check.py exNN` (albo
`python check.py --all`).

**Pamiętaj o dwóch rzeczach.** (1) Po każdej zmianie kodu albo trybu zrestartuj
aplikację; `check.py` pyta Pyroscope tylko o próbki **od startu bieżącego
procesu**, więc po restarcie wygeneruj ruch i poczekaj ok. 15–20 s, aż próbki się
pojawią. (2) Dane z poprzednich uruchomień zostają w wolumenie Pyroscope
(`docker compose down -v` czyści); okna czasu w UI ustawiaj na ostatnie minuty.

Utknąłeś? Najpierw stopniowane podpowiedzi w `solutions/hints/` (kierunek →
API → pseudokod), dopiero potem gotowe wersje w `solutions/` (patrz
`solutions/README.md`).

## Mapa repo

| Ścieżka | Co to |
|---------|-------|
| `app/`       | aplikacja pixelforge (`profiling.py` — warstwa-temat kursu; `images.py`/`fetch.py`/`reports.py`/`storage.py`/`main.py` — domena, działa od startu) |
| `data/`      | korpus obrazów (`scripts/gen_corpus.py`) + runtime storage (`data/uploads/`, poza gitem) |
| `exercises/` | 16 ćwiczeń + `00-teoria.md` + czytanki blokowe (`04a`/`06a`/`09a`/`11a`) + `slownik.md` |
| `solutions/` | gotowe wersje modułów, fragmenty napraw, podpowiedzi, odpowiedzi |
| `scripts/`   | `gen_corpus.py` (korpus), `reset_uploads.py` (czyszczenie uploadów) |
| `check.py`   | maszynowa weryfikacja kryteriów „done" per ćwiczenie |
| `loadgen.py` | generator ruchu (`--concurrency`/`--duration`/`--scenario`/`--pool`/`--report-ids`/`--requests`; scenariusz `pipeline` = to samo żądanie w kółko) |
| `profiles/`  | miejsce na artefakty ćwiczeń (poza gitem) |
| `docker-compose.yml` | Pyroscope + serwis `origin` (nginx; statyczne obrazy do pobierania) |

## Narzędzia użyte w kursie

- **Grafana Pyroscope** (Docker, `:4040`) — continuous profiling, flamegrafy,
  tagowanie, porównywanie profili w czasie.
- **py-spy** — podgląd żywego procesu Pythona z zewnątrz (top/dump/record),
  bez zmiany kodu ani restartu.
- **memray** — profiler pamięci na poziomie alokatora, wykrywanie wycieków
  (`--leaks`).
- **cProfile + snakeviz** — deterministyczny profil offline pojedynczej
  funkcji, wizualizacja w przeglądarce.
- **`tracemalloc`** (stdlib) — śledzenie alokacji Pythona per linia kodu
  (domyślnie wyłączone: spowalnia pętle w czystym Pythonie ok. 11×; włączasz
  `PIXELFORGE_TRACEMALLOC=1` albo pierwszym `GET /debug/memory`).
- **`timeit`** (stdlib) — mikrobenchmarki porównawcze.

## Uwagi

- **Koszt:** kurs nie używa żadnego LLM ani usługi płatnej — $0.
- **Porty:** aplikacja `127.0.0.1:8040` (lokalnie), Pyroscope `127.0.0.1:4040`
  i `origin` `127.0.0.1:8041` (Docker; porty wystawione tylko na pętlę zwrotną).
  Jeśli kolidują z innym programem, zmień w `docker-compose.yml` i `.env` — nie
  uruchamiaj dwóch ciężkich stacków obserwowalności naraz. Nazwy kontenerów
  zależą od projektu compose (`<projekt>-pyroscope-1`, `<projekt>-origin-1`);
  logi: `docker compose logs origin`.
- **py-spy i memray bez `sudo`.** Na macOS `py-spy` zawsze wymaga `sudo` (macOS
  pozwala czytać pamięć innego procesu tylko rootowi lub podpisanemu
  debuggerowi; SIP to osobna blokada chronionych binarek systemowych, której
  nie obchodzi nawet root), podobnie `memray attach`. Ścieżki bez
  uprawnień administratora:
  - **memray:** `memray run -o profiles/plik.bin -m uvicorn app.main:app --host
    127.0.0.1 --port 8040` uruchamia aplikację od razu pod kontrolą memray (nie
    wymaga uprawnień); po zatrzymaniu (Ctrl+C) `memray flamegraph --leaks -o
    profiles/plik.html profiles/plik.bin` (ćwiczenie 8).
  - **py-spy:** w kontenerze Linux
    `docker run --rm -it --cap-add SYS_PTRACE python:3.14-slim …` (w obrazie
    `slim` nie ma `pgrep`, `ps` ani `curl` — PID bierz z `$!`, dla pixelforge
    z `/health`). Przy domyślnej
    izolacji PID kontener nie widzi procesów hosta, więc py-spy zdiagnozuje w
    nim tylko program uruchomiony w tym samym kontenerze. Ćwiczenie 2 bez
    `sudo` wykonujesz więc w całości w jednym kontenerze (aplikacja, loadgen,
    py-spy i `check.py ex02`; jak go przygotować — repozytorium, korpus,
    `docker exec` — opisuje ćwiczenie 2, „Teoria w pigułce”);
    `solutions/gil_demo.py` (ćwiczenie 10) służy tylko do przećwiczenia
    poleceń.
  Na Linuksie bez kontenera podłączenie po PID zwykle wymaga roota; bez niego
  tylko wtedy, gdy pozwalają na to polityka ptrace systemu i Twoje uprawnienia
  (np. `CAP_SYS_PTRACE` albo `kernel.yama.ptrace_scope` = 0).
- **memray NIE działa na Windows** (opiera się na mechanizmach specyficznych
  dla Linux/macOS) — na Windows użyj WSL2.
- **`fsync` na macOS** nie opróżnia sprzętowego cache dysku (to robi
  `F_FULLFSYNC`) — wada z ćwiczenia 14 jest tam słabiej widoczna niż na Linuksie.
- **Nie commituj artefaktów profilowania na stałe** — katalog `profiles/`
  (wygenerowane pliki `.prof`/`.html`/`.bin`/`.txt`/`.md` z ćwiczeń) jest w
  `.gitignore`, podobnie `data/uploads/`.
