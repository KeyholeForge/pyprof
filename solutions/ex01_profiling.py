"""solutions/ex01_profiling.py — the cumulative version of app/profiling.py after exercise 01.

Implemented: init_profiling() (ex. 01). The `wall` parameter is accepted,
but still ignored — you will handle it in exercise 11.

Usage: cp solutions/ex01_profiling.py app/profiling.py
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
    """True if init_profiling() has already been called. Ready from the start."""
    return bool(_STATE["configured"])


def is_wall() -> bool:
    """True if the process started in wall-clock mode (PYROSCOPE_WALL=1)."""
    return bool(_STATE["wall"])


def status() -> dict[str, Any]:
    """The profiling state for GET /health. Ready from the start."""
    return {
        "configured": is_configured(),
        "wall": is_wall(),
        "mode": "wall" if is_wall() else "cpu",
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
    """TODO exercise 04 — see solutions/ex04_profiling.py."""
    raise NotImplementedError(
        "TODO exercise 04: implement tag_wrapper() — see "
        "solutions/ex04_profiling.py and app/profiling.py"
    )
    yield


def start_memory_tracking() -> None:
    """TODO exercise 07 — see solutions/ex07_profiling.py."""
    raise NotImplementedError(
        "TODO exercise 07: implement start_memory_tracking() — see "
        "solutions/ex07_profiling.py and app/profiling.py"
    )


def get_memory_snapshot(top_n: int = 10) -> list[dict[str, Any]]:
    """TODO exercise 07 — see solutions/ex07_profiling.py."""
    raise NotImplementedError(
        "TODO exercise 07: implement get_memory_snapshot() — see "
        "solutions/ex07_profiling.py and app/profiling.py"
    )
