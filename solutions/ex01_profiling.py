"""solutions/ex01_profiling.py — kumulatywna wersja app/profiling.py po ćwiczeniu 01.

Zaimplementowane: init_profiling() (ćw. 01). Parametr `wall` jest przyjęty,
ale jeszcze ignorowany — obsłużysz go w ćwiczeniu 11.

Użycie: cp solutions/ex01_profiling.py app/profiling.py
"""

from __future__ import annotations

import tracemalloc
from contextlib import contextmanager
from typing import Any, Iterator

import pyroscope

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
    resolved_tags = tags or {}
    pyroscope.configure(
        application_name=app_name,
        server_address=server_address,
        sample_rate=100,
        oncpu=True,
        gil_only=True,
        tags=resolved_tags,
    )
    _STATE.update(
        configured=True,
        application_name=app_name,
        server_address=server_address,
        tags=resolved_tags,
    )


@contextmanager
def tag_wrapper(tags: dict[str, str]) -> Iterator[None]:
    """TODO ćwiczenie 04 — zobacz solutions/ex04_profiling.py."""
    raise NotImplementedError(
        "TODO ćwiczenie 04: zaimplementuj tag_wrapper() — zobacz "
        "solutions/ex04_profiling.py i app/profiling.py"
    )
    yield


def start_memory_tracking() -> None:
    """TODO ćwiczenie 07 — zobacz solutions/ex07_profiling.py."""
    raise NotImplementedError(
        "TODO ćwiczenie 07: zaimplementuj start_memory_tracking() — zobacz "
        "solutions/ex07_profiling.py i app/profiling.py"
    )


def get_memory_snapshot(top_n: int = 10) -> list[dict[str, Any]]:
    """TODO ćwiczenie 07 — zobacz solutions/ex07_profiling.py."""
    raise NotImplementedError(
        "TODO ćwiczenie 07: zaimplementuj get_memory_snapshot() — zobacz "
        "solutions/ex07_profiling.py i app/profiling.py"
    )
