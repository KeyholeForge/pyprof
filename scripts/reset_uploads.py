#!/usr/bin/env python3
"""scripts/reset_uploads.py — czyści data/uploads/ (obrazy wgrane przez upload/fetch/filtry).

Uruchom przed każdym pomiarem, żeby wyniki nie zależały od historii poprzednich
biegów loadgenu. Zatrzymaj wcześniej aplikację albo zrestartuj ją po czyszczeniu
(cache miniatur w procesie trzyma ID, których już nie ma na dysku).

    python scripts/reset_uploads.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"


def main() -> None:
    removed = 0
    if UPLOAD_DIR.exists():
        removed = sum(1 for p in UPLOAD_DIR.rglob("*") if p.is_file())
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / "filtered").mkdir(exist_ok=True)
    print(f"reset_uploads: usunięto {removed} plików z {UPLOAD_DIR}")


if __name__ == "__main__":
    main()
