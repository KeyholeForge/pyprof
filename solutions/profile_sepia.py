"""solutions/profile_sepia.py — the reference cProfile script (exercise 03).

Profiles the naive sepia filter from app/images.py OFFLINE (no HTTP server) on
one large corpus image. Result: a .prof file (to open in snakeviz)
+ a text summary on stdout.

How to run (from the repo root, after `python scripts/gen_corpus.py`):
    python solutions/profile_sepia.py

How to view the result:
    snakeviz profiles/ex03_sepia.prof
"""

from __future__ import annotations

import cProfile
import pstats
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from PIL import Image  # noqa: E402

from app.images import _sepia_naive  # noqa: E402

CORPUS_DIR = REPO_ROOT / "data" / "corpus"
OUT_DIR = REPO_ROOT / "profiles"


def main() -> None:
    candidates = sorted(CORPUS_DIR.glob("*_large_*.jpg"))
    if not candidates:
        raise SystemExit(
            f"No large images in {CORPUS_DIR} — run "
            f"`python scripts/gen_corpus.py` first."
        )
    path = candidates[0]
    print(f"Profiling _sepia_naive on: {path.name}")

    with Image.open(path) as img:
        img = img.convert("RGB")

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / "ex03_sepia.prof"

        profiler = cProfile.Profile()
        profiler.enable()
        _sepia_naive(img)
        profiler.disable()

    profiler.dump_stats(str(out_path))
    print(f"Saved: {out_path}")

    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(15)


if __name__ == "__main__":
    main()
