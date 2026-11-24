"""solutions/profile_sepia.py — referencyjny skrypt cProfile (ćwiczenie 03).

Profiluje OFFLINE (bez serwera HTTP) naiwny filtr sepia z app/images.py na
jednym dużym obrazie z korpusu. Wynik: plik .prof (do obejrzenia w snakeviz)
+ tekstowe podsumowanie na stdout.

Uruchomienie (z katalogu głównego repo, po `python scripts/gen_corpus.py`):
    python solutions/profile_sepia.py

Obejrzenie wyniku:
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
            f"Brak dużych obrazów w {CORPUS_DIR} — uruchom najpierw "
            f"`python scripts/gen_corpus.py`."
        )
    path = candidates[0]
    print(f"Profiluję _sepia_naive na: {path.name}")

    with Image.open(path) as img:
        img = img.convert("RGB")

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / "ex03_sepia.prof"

        profiler = cProfile.Profile()
        profiler.enable()
        _sepia_naive(img)
        profiler.disable()

    profiler.dump_stats(str(out_path))
    print(f"Zapisano: {out_path}")

    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(15)


if __name__ == "__main__":
    main()
