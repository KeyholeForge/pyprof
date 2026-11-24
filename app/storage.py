"""Writing result files to disk — used by upload, fetch and the filters.

This module WORKS from the start (it is not the topic layer of the course), but it
deliberately contains the performance flaw F4 (disk) — see the `save_bytes` docstring below.
The fixed version: solutions/storage_snippets.py (exercise 14).
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CHUNK_SIZE = 8192


def save_bytes(path: Path, data: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    """Writes `data` to the file at `path`, creating parent directories as needed.

    PERFORMANCE FLAW (F4, exercise 14 — disk): the data is written in small
    chunks (`chunk_size`), and after EVERY chunk we call `f.flush()` +
    `os.fsync(f.fileno())`. This forces a physical write to the storage medium
    (not just to the file system buffer) after every chunk, instead of buffering
    the whole write and syncing it once at the end. Under loadgen traffic this shows up as:
      - high time in I/O in a wall-clock profile (oncpu=False, exercise 11),
      - lots of fsync()/write() calls in `py-spy dump --locals` or strace,
      - write throughput far lower than the raw disk bandwidth.
    The fixed version (a buffer + one write + one fsync at the end, or no
    fsync at all if durability is not required): solutions/storage_snippets.py.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        for offset in range(0, len(data), chunk_size):
            chunk = data[offset : offset + chunk_size]
            f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
