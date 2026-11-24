#!/usr/bin/env python3
"""check.py — maszynowa weryfikacja kryteriów „done" dla kursu pyprof.

Użycie:
    python check.py ex01        # sprawdza kryteria ćwiczenia 1
    python check.py --all       # sprawdza wszystkie zaimplementowane ćwiczenia

Dwa rodzaje asercji:
  - PLIKOWE / statyczne (grep po app/*.py, istnienie plików w profiles/) —
    działają zawsze, nie wymagają uruchomionej aplikacji ani Dockera.
  - SIECIOWE (HTTP do aplikacji :8040 i/lub Pyroscope :4040) — jeśli serwis
    nie odpowiada w ciągu 2s, wynik to SKIP (nie FAIL) — brak infrastruktury
    nie jest tym samym co niezaliczone ćwiczenie.

Kryteria niesprawdzalne maszynowo (np. „rozumiesz dlaczego") zostają tylko
w treści ćwiczeń, nie tutaj.
"""

from __future__ import annotations

import json
import pstats
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
APP_DIR = REPO_ROOT / "app"
PROFILES_DIR = REPO_ROOT / "profiles"

APP_BASE_URL = "http://127.0.0.1:8040"
PYROSCOPE_BASE_URL = "http://127.0.0.1:4040"
HTTP_TIMEOUT = 2.0


class Skip(Exception):
    """Podnoszona, gdy asercja wymaga niedostępnej infrastruktury (nie FAIL)."""


class Fail(Exception):
    """Podnoszona, gdy asercja wykonała się, ale kryterium nie jest spełnione."""


# --- pomocnicze --------------------------------------------------------------


def _read(path: Path) -> str:
    if not path.exists():
        raise Fail(f"Brak pliku: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def _read_artifact(name: str) -> str:
    """Treść artefaktu z profiles/ — musi istnieć, nie być pusta ani szablonem."""
    path = PROFILES_DIR / name
    _file_nonempty(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if "PLACEHOLDER" in text:
        raise Fail(f"profiles/{name} zawiera PLACEHOLDER — zapisz własny wynik.")
    return text


def _file_nonempty(path: Path) -> None:
    if not path.exists():
        raise Fail(
            f"Brak pliku {path.relative_to(REPO_ROOT)} — wygeneruj go zgodnie "
            f"z krokami ćwiczenia."
        )
    if path.stat().st_size == 0:
        raise Fail(f"Plik {path.relative_to(REPO_ROOT)} jest pusty.")


def _http_json(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            status = resp.status
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = exc.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise Skip(f"Niedostępne: {url} ({exc})")
    try:
        parsed = json.loads(payload) if payload else {}
    except json.JSONDecodeError:
        parsed = {}
    return {"status": status, "body": parsed}


def _health() -> dict:
    """GET /health — 200 i JSON ze stanem aplikacji (pid, started_at, profiling)."""
    resp = _http_json("GET", f"{APP_BASE_URL}/health")
    if resp["status"] != 200:
        raise Fail(f"GET /health → HTTP {resp['status']}, oczekiwano 200")
    return resp["body"]


def _pyroscope_samples(selector: str, since: float) -> int:
    """Łączna wartość profilu (`numTicks`) w Pyroscope od chwili `since` (epoka, sekundy).

    Pytamy o okno OD STARTU APLIKACJI (najwyżej ostatnia godzina), a nie
    ogólnie o „ostatnią godzinę" — Pyroscope pamięta dane z wcześniejszych
    uruchomień (także z rozwiązań), które nie mogą się liczyć. Zapytanie
    filtruje po oknie czasu i etykietach, nie po procesie ani trybie profilera:
    próbki innego procesu tej samej usługi wysłane w tym oknie też by się liczyły.
    Wartość w jednostkach profilu (ns zagregowanej wagi próbek), nie liczba
    próbek; 0 = brak danych.
    """
    now = time.time()
    query = f"process_cpu:cpu:nanoseconds:cpu:nanoseconds{{{selector}}}"
    params = urllib.parse.urlencode(
        {
            "query": query,
            "from": int(max(since, now - 3600) * 1000),
            "until": int(now * 1000),
            "format": "json",
        }
    )
    url = f"{PYROSCOPE_BASE_URL}/pyroscope/render?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:  # przed URLError: HTTPError to jego podklasa
        raise Fail(f"Pyroscope render → HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise Skip(f"Niedostępne: {url} ({exc})")
    return int(body.get("flamebearer", {}).get("numTicks", 0))


# --- asercje per ćwiczenie -----------------------------------------------


def check_ex01() -> str:
    """Ćw. 01: init_profiling — aplikacja wysyła próbki do Pyroscope."""
    health = _health()
    if not health.get("profiling", {}).get("configured"):
        raise Fail(
            "GET /health: profiling.configured = false — init_profiling() "
            "nie zadziałało (szkielet z TODO?). Zaimplementuj je w "
            "app/profiling.py i zrestartuj aplikację."
        )
    ticks = _pyroscope_samples('service_name="pixelforge"', health["started_at"])
    if ticks == 0:
        raise Fail(
            "Pyroscope nie ma próbek service_name='pixelforge' z okna od startu "
            "aplikacji (najwyżej ostatnia godzina). Wygeneruj ruch (python loadgen.py "
            "--duration 20 --concurrency 3) i poczekaj ok. 15-20 s, aż próbki dojdą."
        )
    return (
        "/health: profiling.configured; Pyroscope ma próbki pixelforge z okna "
        "od startu aplikacji (najwyżej ostatnia godzina) "
        f"({ticks / 1e9:.2f} s zagregowanej wagi próbek)"
    )


def check_ex02() -> str:
    """Ćw. 02: py-spy top/dump na żywym procesie — zapisany snapshot."""
    text = _read_artifact("ex02_dump.txt")
    if "Thread" not in text or "app/" not in text:
        raise Fail(
            "profiles/ex02_dump.txt nie wygląda jak wynik `py-spy dump --locals` "
            "z aplikacji pixelforge (brak słowa 'Thread' i/lub ścieżek 'app/'). "
            "Zrób zrzut, póki loadgen jeszcze generuje ruch — po jego zakończeniu "
            "wątki czekają poza kodem app/."
        )
    return (
        "profiles/ex02_dump.txt: wygląda na zrzut stosów wątków z ramkami app/ "
        "(heurystyka treści — 'Process <pid>' porównaj z /health samodzielnie)"
    )


def check_ex03() -> str:
    """Ćw. 03: cProfile + snakeviz — zapisany profil .prof."""
    path = PROFILES_DIR / "ex03_sepia.prof"
    _file_nonempty(path)
    try:
        stats = pstats.Stats(str(path))
    except Exception as exc:  # noqa: BLE001
        raise Fail(f"profiles/ex03_sepia.prof nie jest poprawnym plikiem cProfile: {exc!r}")
    if not any(func[2] == "_sepia_naive" for func in stats.stats):
        raise Fail("W profiles/ex03_sepia.prof nie ma funkcji _sepia_naive — profilujesz złą ścieżkę.")
    return "profiles/ex03_sepia.prof: poprawny cProfile, widać _sepia_naive"


def check_ex04() -> str:
    """Ćw. 04: tag_wrapper — tagi per-endpoint widoczne w Pyroscope."""
    health = _health()
    ticks = _pyroscope_samples('service_name="pixelforge",endpoint=~".+"', health["started_at"])
    if ticks == 0:
        raise Fail(
            "Pyroscope nie ma próbek pixelforge z tagiem 'endpoint' z okna od startu "
            "aplikacji (najwyżej ostatnia godzina) — sprawdź tag_wrapper() w "
            "app/profiling.py i wygeneruj ruch "
            "(python loadgen.py --duration 15) PO restarcie aplikacji."
        )
    return (
        "Pyroscope ma próbki pixelforge z tagiem 'endpoint' z okna od startu "
        "aplikacji (najwyżej ostatnia godzina) "
        f"({ticks / 1e9:.2f} s zagregowanej wagi próbek)"
    )


def check_ex05() -> str:
    """Ćw. 05: naprawa naiwnej sepii — Image.convert(matrix=...) zamiast pętli."""
    src = _read(APP_DIR / "images.py")
    # Uwaga: NIE sprawdzamy samego 'convert("RGB", matrix=' — ten fragment
    # występuje też w docstringu _sepia_naive jako opis naprawy (fałszywy PASS
    # na niezmienionym kodzie). Szukamy konkretnie użycia SEPIA_MATRIX w kodzie.
    if "matrix=SEPIA_MATRIX" not in src:
        raise Fail(
            "app/images.py wciąż liczy sepię naiwną pętlą Pythona — zamień "
            "wywołanie _sepia_naive(img) na img.convert(\"RGB\", "
            "matrix=SEPIA_MATRIX) (patrz solutions/filters_fragmenty.py)."
        )
    return "app/images.py: filtr sepia liczony przez Image.convert(matrix=...)"


def check_ex06() -> str:
    """Ćw. 06: mikrobenchmarki timeit — zapisane wyniki."""
    text = _read_artifact("ex06_timeit.txt")
    if len(re.findall(r"loops?, best of", text)) < 2:
        raise Fail("profiles/ex06_timeit.txt: oczekiwano dwóch wyników `python -m timeit` (naiwna i Pillow).")
    return "profiles/ex06_timeit.txt: dwa wyniki timeit (naiwna vs Pillow)"


def check_ex07() -> str:
    """Ćw. 07: tracemalloc przez /debug/memory (dwa wywołania, drugie musi mieć dane)."""
    first = _http_json("GET", f"{APP_BASE_URL}/debug/memory")
    if first["status"] == 501:
        raise Fail("GET /debug/memory → 501: profiling.py jeszcze niezaimplementowane")
    if first["status"] != 200:
        raise Fail(f"GET /debug/memory → HTTP {first['status']}, oczekiwano 200")
    resp = _http_json("GET", f"{APP_BASE_URL}/debug/memory")
    top = resp["body"].get("top_allocations", [])
    if not top:
        raise Fail(
            "GET /debug/memory zwróciło pustą listę top_allocations — "
            "tracemalloc nie działa (start_memory_tracking() powinno być wołane w lifespan)."
        )
    if not {"file", "line", "size_kb", "count"} <= set(top[0]):
        raise Fail(f"Pozycja top_allocations ma złe pola: {top[0]}")
    return f"GET /debug/memory → 200, {len(top)} pozycji top_allocations"


def check_ex08() -> str:
    """Ćw. 08: naprawa wycieku THUMBNAIL_CACHE (W1) + memray --leaks."""
    html = _read_artifact("ex08_leak.html")
    if "images.py" not in html:
        raise Fail("profiles/ex08_leak.html nie zawiera 'images.py' — to nie jest raport memray z pixelforge.")
    src = _read(APP_DIR / "images.py")
    # Uwaga: NIE sprawdzamy samych słów-kluczy typu "TTL"/"lru_cache" — one
    # występują też w docstringu THUMBNAIL_CACHE jako OPIS możliwej naprawy
    # (fałszywy PASS na niezmienionym kodzie). Szukamy konkretnych funkcji,
    # które faktycznie implementują evikcję (patrz solutions/images_fragmenty.py).
    if "_cache_get" not in src or "_cache_put" not in src:
        raise Fail(
            "app/images.py: nie widać funkcji _cache_get/_cache_put ani innej "
            "konkretnej implementacji evikcji — THUMBNAIL_CACHE wciąż rośnie "
            "bez ograniczeń (patrz solutions/images_fragmenty.py)."
        )
    return "profiles/ex08_leak.html zapisany; app/images.py ma logikę evikcji cache"


def _live_pipeline_growth(requests: int = 30) -> tuple[int, int]:
    """Uruchamia W PROCESIE check.py `requests` identycznych żądań potoku (W1b) i
    zwraca (żywe FilterPipeline, subskrybenci szyny EVENTS po odjęciu stanu początkowego).

    Test jest behawioralny (liczy żywe obiekty przez gc), więc nie da się go
    oszukać komentarzem ani docstringiem w kodzie, i nie wymaga działającej aplikacji.
    """
    import gc
    import importlib

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        images = importlib.import_module("app.images")
        pipeline = importlib.import_module("app.pipeline")
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        raise Fail(f"Nie da się zaimportować app.images / app.pipeline: {exc!r}")
    config = importlib.import_module("app.config")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    probe = config.UPLOAD_DIR / "ex09check.jpg"
    Image.new("RGB", (200, 150), (90, 120, 200)).save(probe, format="JPEG")
    try:
        before = len(pipeline.EVENTS)
        for _ in range(requests):
            images.apply_pipeline("ex09check", "szkic")
        gc.collect()
        live = sum(1 for o in gc.get_objects() if type(o) is pipeline.FilterPipeline)
        return live, len(pipeline.EVENTS) - before
    except Exception as exc:  # noqa: BLE001
        raise Fail(f"images.apply_pipeline('ex09check', 'szkic') rzuciło wyjątek: {exc!r}")
    finally:
        probe.unlink(missing_ok=True)


def check_ex09() -> str:
    """Ćw. 09: naprawa wycieku W1b (graf per żądanie rejestrowany w EVENTS) + notatki z diagnozy."""
    requests = 30
    live, subscribers = _live_pipeline_growth(requests)
    # Stała, nie funkcja liczby żądań: współdzielony graf = 1 (na preset), unsubscribe w finally = 0.
    if live > 2 or subscribers > 2:
        raise Fail(
            f"Po {requests} identycznych żądaniach żyje {live} obiektów FilterPipeline, a szyna EVENTS "
            f"urosła o {subscribers} nasłuchujących — graf wciąż wycieka (liczba rośnie z liczbą żądań). "
            f"Napraw w app/images.py (patrz solutions/pipeline_fragmenty.py)."
        )
    html = _read_artifact("ex09_leak.html")
    if "pipeline.py" not in html:
        raise Fail(
            "profiles/ex09_leak.html nie zawiera 'pipeline.py' — to nie jest raport memray --leaks "
            "z ruchu na /pipeline (stan PRZED naprawą, zachowany jako dowód diagnozy)."
        )
    src = _read(APP_DIR / "reports.py")
    if re.search(r'report\s*\+=\s*f"', src):
        raise Fail("app/reports.py ma konkatenację 'report +=' w pętli — przywróć listę + join (★ W7).")
    notes = _read_artifact("ex09_notes.md")
    missing = [w for w in ("get_referrers", "EVENTS") if w not in notes]
    if len(notes) < 200 or missing:
        raise Fail(
            "profiles/ex09_notes.md: zapisz liczby (RSS/liczba instancji przed i po), łańcuch referencji z "
            "gc.get_referrers do EVENTS i uzasadnienie wyboru naprawy (min. 200 znaków; słowa "
            f"`get_referrers` i `EVENTS`){'; brakuje: ' + ', '.join(missing) if missing else ''}."
        )
    return (
        f"po {requests} identycznych żądaniach: {live} żywych FilterPipeline, szyna +{subscribers}; "
        "ex09_leak.html i ex09_notes.md zapisane"
    )


def check_ex10() -> str:
    """Ćw. 10: GIL — porównanie threads vs processes (gil_demo.py)."""
    text = _read_artifact("ex10_gil_notes.txt")
    numbers = re.findall(r"\d+[.,]\d+", text)
    if len(numbers) < 3 or not all(w in text.lower() for w in ("sequential", "threads", "processes")):
        raise Fail(
            "profiles/ex10_gil_notes.txt: oczekiwano trzech czasów (sequential, "
            "threads, processes) z częścią dziesiętną, np. 'sequential 0.65 s'."
        )
    return f"profiles/ex10_gil_notes.txt: {len(numbers)} liczb, trzy tryby opisane"


def check_ex11() -> str:
    """Ćw. 11: tryb wall-clock wybrany przy starcie — próbki z tagiem tryb=wall."""
    health = _health()
    prof = health.get("profiling", {})
    if not prof.get("configured"):
        raise Fail("GET /health: profiling.configured = false — najpierw ćwiczenie 01.")
    if not prof.get("wall"):
        raise Fail(
            "Aplikacja działa w trybie CPU (profiling.wall = false). Uruchom ją "
            "ponownie z PYROSCOPE_WALL=1 (tryb wybiera się przy starcie procesu) "
            "i upewnij się, że init_profiling() obsługuje parametr `wall`."
        )
    ticks = _pyroscope_samples('service_name="pixelforge",tryb="wall"', health["started_at"])
    if ticks == 0:
        raise Fail(
            "Brak próbek z tagiem tryb=wall od startu procesu — init_profiling() "
            "powinno dodać tag tryb=wall i oncpu=False, gil_only=False. "
            "Wygeneruj ruch i poczekaj ok. 15-20 s."
        )
    return f"/health: tryb wall; Pyroscope ma próbki tryb=wall od startu procesu ({ticks / 1e9:.1f} s)"


def check_ex12() -> str:
    """Ćw. 12: naprawa W3a — współdzielony httpx.AsyncClient."""
    fetch_src = _read(APP_DIR / "fetch.py")
    main_src = _read(APP_DIR / "main.py")
    if "async with httpx.AsyncClient() as client:" in fetch_src:
        raise Fail(
            "app/fetch.py wciąż tworzy nowego httpx.AsyncClient() per wywołanie "
            "— przenieś klienta do app.state (patrz solutions/fetch_fragmenty.py)."
        )
    if "http_client" not in main_src:
        raise Fail(
            "app/main.py: nie widać współdzielonego klienta w app.state "
            "(oczekiwano np. app.state.http_client w lifespan)."
        )
    return "Brak httpx.AsyncClient() per-request; klient współdzielony w app.state"


def check_ex13() -> str:
    """Ćw. 13: naprawa W3b — fetch_batch równolegle przez asyncio.gather."""
    src = _read(APP_DIR / "fetch.py")
    # Uwaga: NIE wystarczy szukać substringu "asyncio.gather" — występuje też
    # w docstringu jako opis naprawy (fałszywy PASS na niezmienionym kodzie).
    # Szukamy REALNEGO wywołania (await ... asyncio.gather().
    if not re.search(r"await\s+asyncio\.gather\(", src):
        raise Fail(
            "app/fetch.py: fetch_batch wciąż pobiera URL-e sekwencyjnie w pętli "
            "for — zamień na `await asyncio.gather(...)` (patrz "
            "solutions/fetch_fragmenty.py)."
        )
    return "app/fetch.py: fetch_batch używa asyncio.gather"


def check_ex14() -> str:
    """Ćw. 14: naprawa W4 — bufor + jeden zapis/fsync zamiast fsync per chunk."""
    src = _read(APP_DIR / "storage.py")
    if "for offset in range(0, len(data), chunk_size):" in src:
        raise Fail(
            "app/storage.py: save_bytes wciąż dzieli zapis na chunki z "
            "flush()+fsync() po każdym — zamień na jeden f.write(data) + jeden "
            "fsync (patrz solutions/storage_fragmenty.py)."
        )
    return "app/storage.py: save_bytes zapisuje jednym write() (bez fsync per chunk)"


def check_ex15() -> str:
    """Ćw. 15: porównanie profili w czasie (tag version) — notatki zapisane."""
    text = _read_artifact("ex15_comparison.md")
    if "version" not in text or len(text) < 200:
        raise Fail("profiles/ex15_comparison.md: opisz porównanie tagu `version` (min. 200 znaków, wspomnij `version`).")
    return "profiles/ex15_comparison.md: opis porównania wersji"


def check_ex16() -> str:
    """Ćw. 16: finałowy challenge — własna diagnoza PRZED sprawdzeniem klucza."""
    text = _read_artifact("ex16_diagnosis.md")
    if text.count("→") < 4:
        raise Fail("profiles/ex16_diagnosis.md: dla każdego z 4 objawów zapisz „objaw → ślad → hipoteza\" (min. 4 strzałki →).")
    if not (REPO_ROOT / "solutions" / "ex16_odpowiedzi.md").exists():
        raise Fail("Brak solutions/ex16_odpowiedzi.md (błąd budowy kursu, zgłoś).")
    return "profiles/ex16_diagnosis.md zapisany (Twoja diagnoza)"


CHECKS = {
    "ex01": check_ex01,
    "ex02": check_ex02,
    "ex03": check_ex03,
    "ex04": check_ex04,
    "ex05": check_ex05,
    "ex06": check_ex06,
    "ex07": check_ex07,
    "ex08": check_ex08,
    "ex09": check_ex09,
    "ex10": check_ex10,
    "ex11": check_ex11,
    "ex12": check_ex12,
    "ex13": check_ex13,
    "ex14": check_ex14,
    "ex15": check_ex15,
    "ex16": check_ex16,
}


def run_one(name: str) -> str:
    fn = CHECKS.get(name)
    if fn is None:
        print(f"Nieznane ćwiczenie: {name}. Dostępne: {', '.join(sorted(CHECKS))}")
        return "UNKNOWN"
    try:
        detail = fn()
        print(f"[PASS] {name}: {detail}")
        return "PASS"
    except Skip as exc:
        print(f"[SKIP] {name}: {exc}")
        return "SKIP"
    except Fail as exc:
        print(f"[FAIL] {name}: {exc}")
        return "FAIL"
    except Exception as exc:  # noqa: BLE001 — nieoczekiwany błąd też ma być widoczny
        print(f"[FAIL] {name}: nieoczekiwany błąd: {exc!r}")
        return "FAIL"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    arg = sys.argv[1]
    if arg == "--all":
        results = {name: run_one(name) for name in CHECKS}
        print()
        print("=== Podsumowanie ===")
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for name, result in results.items():
            counts[result] = counts.get(result, 0) + 1
        for name, result in results.items():
            print(f"  {name}: {result}")
        print(
            f"Razem: {counts.get('PASS', 0)} PASS, {counts.get('FAIL', 0)} FAIL, "
            f"{counts.get('SKIP', 0)} SKIP (na {len(results)} ćwiczeń)"
        )
        if counts.get("FAIL", 0) > 0:
            raise SystemExit(1)
    else:
        result = run_one(arg)
        if result in ("FAIL", "UNKNOWN"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
