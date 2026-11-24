#!/usr/bin/env python3
"""scripts/reset_uploads.py — cleans data/uploads/ (images saved by upload/fetch/filters).

Run it before every measurement, so the results do not depend on the history of previous
loadgen runs. Stop the application first or restart it after cleaning
(the thumbnail cache in the process holds IDs that no longer exist on disk).

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
    print(f"reset_uploads: removed {removed} files from {UPLOAD_DIR}")


if __name__ == "__main__":
    main()
