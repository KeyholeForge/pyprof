"""app/profiling.py — the topic layer of the pyprof course: profiling instrumentation.

This is the ONLY module of the course with a TODO skeleton. All the other modules (images,
fetch, reports, storage, main) are complete and work from the start — the learner does NOT
write domain logic, only fills in the functions below in successive exercises.
The rest of the application imports this module and catches `NotImplementedError` to
return a readable HTTP 501 instead of crashing the whole service.

Cumulative, WORKING versions of this file:
  solutions/ex01_profiling.py    — init_profiling
  solutions/ex04_profiling.py    — + tag_wrapper
  solutions/ex07_profiling.py    — + start_memory_tracking / get_memory_snapshot
  solutions/ex11_profiling.py    — + wall mode in init_profiling (= the final version)
  solutions/exFINAL_profiling.py — a copy of ex11, to copy over app/profiling.py
                                   when everything should work at once (e.g. ex. 16).

The sampling mode (CPU or wall-clock) is chosen ONCE, at process start
(the PYROSCOPE_WALL=1 environment variable -> the `wall` parameter). On
pyroscope-io 1.4.0, calling pyroscope.configure() again while the agent is
running is refused and changes neither the mode nor the tags.
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
    """TODO exercise 01: connect the application to Pyroscope.

    Call `pyroscope.configure(...)` (pyroscope-io 1.4.0) with the parameters:
      - application_name=app_name
      - server_address=server_address
      - sample_rate=100     (default)
      - oncpu=True          (a CPU profile, not wall-clock)
      - gil_only=True       (only threads holding the GIL)
      - tags=tags or {}
    After configuring, save the parameters in _STATE and set _STATE["configured"] = True.
    Leave the `wall` parameter unused for now — you will handle it in exercise 11.

    See solutions/ex01_profiling.py.
    """
    raise NotImplementedError(
        "TODO exercise 01: implement init_profiling() — see "
        "solutions/ex01_profiling.py and app/profiling.py"
    )


@contextmanager
def tag_wrapper(tags: dict[str, str]) -> Iterator[None]:
    """TODO exercise 04: tag a piece of code in Pyroscope per endpoint.

    `pyroscope.tag_wrapper(tags: dict)` is a context manager that, for the duration
    of the `with` block, adds tags to the samples collected IN THIS THREAD.
    Target usage (see app/main.py, the `_instrumented` helper):
        with tag_wrapper({"endpoint": "thumbnail"}):
            ... endpoint code ...

    See solutions/ex04_profiling.py.
    """
    raise NotImplementedError(
        "TODO exercise 04: implement tag_wrapper() — see "
        "solutions/ex04_profiling.py and app/profiling.py"
    )
    yield  # unreachable — keeps the generator shape required by @contextmanager


def start_memory_tracking() -> None:
    """TODO exercise 07: start allocation tracking (tracemalloc).

    Call `tracemalloc.start()` — but only if it is not running yet
    (`tracemalloc.is_tracing()`), so that a repeated call does not reset the
    collected history. main.py calls this function at application start when PIXELFORGE_TRACEMALLOC=1.

    See solutions/ex07_profiling.py.
    """
    raise NotImplementedError(
        "TODO exercise 07: implement start_memory_tracking() — see "
        "solutions/ex07_profiling.py and app/profiling.py"
    )


def get_memory_snapshot(top_n: int = 10) -> list[dict[str, Any]]:
    """TODO exercise 07: take a tracemalloc snapshot and return the top_n allocations.

    `tracemalloc.take_snapshot().statistics("lineno")` returns a list sorted
    by size, descending. Map the first `top_n` to the GET /debug/memory format:

        [{"file": "...", "line": 42, "size_kb": 123.4, "count": 10}, ...]

    If tracemalloc is not running yet, start it (start_memory_tracking())
    and return an empty list — the data will appear on the next call, after traffic.

    See solutions/ex07_profiling.py.
    """
    raise NotImplementedError(
        "TODO exercise 07: implement get_memory_snapshot() — see "
        "solutions/ex07_profiling.py and app/profiling.py"
    )
