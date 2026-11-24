"""Zapis plików wynikowych na dysk — używany przez upload, fetch i filtry.

Ten moduł DZIAŁA od startu (nie jest warstwą-tematem kursu), ale celowo
zawiera wadę wydajnościową W4 (dysk) — patrz docstring `save_bytes` niżej.
Naprawiona wersja: solutions/storage_fragmenty.py (ćwiczenie 14).
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CHUNK_SIZE = 8192


def save_bytes(path: Path, data: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    """Zapisuje `data` do pliku pod `path`, tworząc katalogi nadrzędne w razie potrzeby.

    WADA WYDAJNOŚCIOWA (W4, ćwiczenie 14 — dysk): dane są zapisywane małymi
    kawałkami (`chunk_size`), a po KAŻDYM kawałku wywołujemy `f.flush()` +
    `os.fsync(f.fileno())`. To wymusza fizyczny zapis na nośnik (nie tylko do
    bufora systemu plików) po każdym chunku, zamiast zbuforować cały zapis
    i zsynchronizować go raz na końcu. Pod obciążeniem loadgenu widać to jako:
      - wysoki czas w I/O w profilu wall-clock (oncpu=False, ćwiczenie 11),
      - mnóstwo wywołań fsync()/write() w `py-spy dump --locals` lub strace,
      - throughput zapisu dużo niższy niż surowa przepustowość dysku.
    Naprawiona wersja (bufor + jeden zapis + jeden fsync na końcu, albo bez
    fsync wcale jeśli trwałość nie jest wymagana): solutions/storage_fragmenty.py.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        for offset in range(0, len(data), chunk_size):
            chunk = data[offset : offset + chunk_size]
            f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
