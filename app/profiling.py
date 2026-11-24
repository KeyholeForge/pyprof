"""app/profiling.py — warstwa-temat kursu pyprof: instrumentacja profilowania.

To JEDYNY moduł kursu ze szkieletem TODO. Wszystkie inne moduły (images,
fetch, reports, storage, main) są kompletne i działają od startu — uczeń NIE
pisze logiki domenowej, tylko wypełnia funkcje poniżej w kolejnych ćwiczeniach.
Reszta aplikacji importuje ten moduł i łapie `NotImplementedError`, żeby
zwrócić czytelne HTTP 501 zamiast crashować cały serwis.

Kumulatywne, DZIAŁAJĄCE wersje tego pliku:
  solutions/ex01_profiling.py    — init_profiling
  solutions/ex04_profiling.py    — + tag_wrapper
  solutions/ex07_profiling.py    — + start_memory_tracking / get_memory_snapshot
  solutions/ex11_profiling.py    — + tryb wall w init_profiling (= wersja finalna)
  solutions/exFINAL_profiling.py — kopia ex11, do skopiowania na app/profiling.py
                                   gdy wszystko ma działać naraz (np. ćw. 16).

Tryb próbkowania (CPU albo wall-clock) wybiera się RAZ, przy starcie procesu
(zmienna środowiskowa PYROSCOPE_WALL=1 → parametr `wall`). W pyroscope-io
1.4.0 ponowne pyroscope.configure(), gdy agent działa, jest odrzucane i nie
zmienia ani trybu, ani tagów.
"""

from __future__ import annotations

import tracemalloc
from contextlib import contextmanager
from typing import Any, Iterator

_STATE: dict[str, Any] = {
    "configured": False,
    "application_name": None,
    "server_address": None,
    "tags": None,
    "wall": False,
}


def is_configured() -> bool:
    """True, jeśli init_profiling() zostało już wywołane. Gotowe od startu."""
    return bool(_STATE["configured"])


def is_wall() -> bool:
    """True, jeśli proces wystartował w trybie wall-clock (PYROSCOPE_WALL=1)."""
    return bool(_STATE["wall"])


def status() -> dict[str, Any]:
    """Stan profilowania dla GET /health. Gotowe od startu."""
    return {
        "configured": is_configured(),
        "wall": is_wall(),
        "tryb": "wall" if is_wall() else "cpu",
        "tracemalloc": tracemalloc.is_tracing(),
    }


def init_profiling(
    app_name: str,
    server_address: str,
    tags: dict[str, str] | None = None,
    wall: bool = False,
) -> None:
    """TODO ćwiczenie 01: podłącz aplikację do Pyroscope.

    Wywołaj `pyroscope.configure(...)` (pyroscope-io 1.4.0) z parametrami:
      - application_name=app_name
      - server_address=server_address
      - sample_rate=100     (domyślnie)
      - oncpu=True          (profil CPU, nie wall-clock)
      - gil_only=True       (tylko wątki trzymające GIL)
      - tags=tags or {}
    Po konfiguracji zapisz parametry w _STATE i ustaw _STATE["configured"] = True.
    Parametr `wall` zostaw na razie nieużyty — obsłużysz go w ćwiczeniu 11.

    Zobacz solutions/ex01_profiling.py.
    """
    raise NotImplementedError(
        "TODO ćwiczenie 01: zaimplementuj init_profiling() — zobacz "
        "solutions/ex01_profiling.py i app/profiling.py"
    )


@contextmanager
def tag_wrapper(tags: dict[str, str]) -> Iterator[None]:
    """TODO ćwiczenie 04: otaguj fragment kodu w Pyroscope per-endpoint.

    `pyroscope.tag_wrapper(tags: dict)` to context manager, który na czas
    bloku `with` dokłada tagi do próbek zebranych w TYM WĄTKU.
    Docelowe użycie (patrz app/main.py, helper `_instrumented`):
        with tag_wrapper({"endpoint": "thumbnail"}):
            ... kod endpointu ...

    Zobacz solutions/ex04_profiling.py.
    """
    raise NotImplementedError(
        "TODO ćwiczenie 04: zaimplementuj tag_wrapper() — zobacz "
        "solutions/ex04_profiling.py i app/profiling.py"
    )
    yield  # nieosiągalne — zachowuje kształt generatora dla @contextmanager


def start_memory_tracking() -> None:
    """TODO ćwiczenie 07: uruchom śledzenie alokacji (tracemalloc).

    Wywołaj `tracemalloc.start()` — ale tylko jeśli jeszcze nie działa
    (`tracemalloc.is_tracing()`), żeby powtórne wywołanie nie resetowało
    zebranej historii. main.py woła tę funkcję przy starcie aplikacji, gdy PIXELFORGE_TRACEMALLOC=1.

    Zobacz solutions/ex07_profiling.py.
    """
    raise NotImplementedError(
        "TODO ćwiczenie 07: zaimplementuj start_memory_tracking() — zobacz "
        "solutions/ex07_profiling.py i app/profiling.py"
    )


def get_memory_snapshot(top_n: int = 10) -> list[dict[str, Any]]:
    """TODO ćwiczenie 07: zrób snapshot tracemalloc i zwróć top_n alokacji.

    `tracemalloc.take_snapshot().statistics("lineno")` zwraca listę posortowaną
    malejąco po rozmiarze. Zmapuj pierwsze `top_n` na format GET /debug/memory:

        [{"file": "...", "line": 42, "size_kb": 123.4, "count": 10}, ...]

    Jeśli tracemalloc jeszcze nie działa, uruchom je (start_memory_tracking())
    i zwróć pustą listę — dane pojawią się przy kolejnym wywołaniu, po ruchu.

    Zobacz solutions/ex07_profiling.py.
    """
    raise NotImplementedError(
        "TODO ćwiczenie 07: zaimplementuj get_memory_snapshot() — zobacz "
        "solutions/ex07_profiling.py i app/profiling.py"
    )
