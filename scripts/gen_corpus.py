#!/usr/bin/env python3
"""Generuje DETERMINISTYCZNY korpus obrazów testowych dla kursu pyprof.

Nie pobiera niczego z internetu — wszystkie obrazy są rysowane lokalnie przez
Pillow (PIL.ImageDraw) z ustalonym seedem, więc wynik jest w 100% powtarzalny.

Dwa katalogi wyjściowe:
  data/corpus/          - duży korpus (>=300 obrazów) do zasilania aplikacji
                           pixelforge (upload/miniatury/filtry) i loadgenu.
                           NIE commitowany (patrz .gitignore).
  data/origin_images/    - mniejszy zestaw (20 obrazów) serwowany przez serwis
                           `origin` w docker-compose.yml pod http://127.0.0.1:8041.
                           Musi istnieć i mieć zawartość PRZED `docker compose up`,
                           bo origin montuje ten katalog jako wolumen tylko-do-odczytu.

Uruchomienie:
    python scripts/gen_corpus.py
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

SEED = 42

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "data" / "corpus"
ORIGIN_DIR = REPO_ROOT / "data" / "origin_images"

# Rozmiary: mała / średnia / duża (szerokość, wysokość)
SIZES = {
    "small": (200, 200),
    "medium": (800, 600),
    "large": (2000, 1500),
}

# Rozkład rozmiarów w głównym korpusie (proporcje sumujące się do 1.0)
CORPUS_SIZE_WEIGHTS = {"small": 0.5, "medium": 0.35, "large": 0.15}

CORPUS_COUNT = 320
ORIGIN_COUNT = 20

JPEG_QUALITY = 85

PATTERNS = ["gradient", "checkerboard", "shapes"]


def _rand_color(rng: random.Random) -> tuple[int, int, int]:
    return (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))


def draw_gradient(img: Image.Image, rng: random.Random) -> None:
    w, h = img.size
    c1 = _rand_color(rng)
    c2 = _rand_color(rng)
    pixels = img.load()
    for x in range(w):
        t = x / max(w - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        for y in range(h):
            pixels[x, y] = (r, g, b)


def draw_checkerboard(img: Image.Image, rng: random.Random) -> None:
    w, h = img.size
    draw = ImageDraw.Draw(img)
    tile = rng.choice([10, 20, 25, 40])
    c1 = _rand_color(rng)
    c2 = _rand_color(rng)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            color = c1 if ((x // tile) + (y // tile)) % 2 == 0 else c2
            draw.rectangle([x, y, x + tile, y + tile], fill=color)


def draw_shapes(img: Image.Image, rng: random.Random) -> None:
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w, h], fill=_rand_color(rng))
    n_shapes = rng.randint(5, 15)
    for _ in range(n_shapes):
        shape_kind = rng.choice(["ellipse", "rectangle", "line"])
        x0, y0 = rng.randint(0, w), rng.randint(0, h)
        x1, y1 = rng.randint(0, w), rng.randint(0, h)
        color = _rand_color(rng)
        xs = sorted([x0, x1])
        ys = sorted([y0, y1])
        box = [xs[0], ys[0], xs[1], ys[1]]
        if shape_kind == "ellipse":
            draw.ellipse(box, fill=color)
        elif shape_kind == "rectangle":
            draw.rectangle(box, fill=color)
        else:
            draw.line([x0, y0, x1, y1], fill=color, width=rng.randint(1, 8))


DRAWERS = {
    "gradient": draw_gradient,
    "checkerboard": draw_checkerboard,
    "shapes": draw_shapes,
}


@dataclass
class GenStats:
    count: int = 0
    total_bytes: int = 0


def weighted_size_choice(rng: random.Random) -> str:
    names = list(CORPUS_SIZE_WEIGHTS.keys())
    weights = list(CORPUS_SIZE_WEIGHTS.values())
    return rng.choices(names, weights=weights, k=1)[0]


def generate_image(size_name: str, pattern: str, rng: random.Random) -> Image.Image:
    size = SIZES[size_name]
    img = Image.new("RGB", size, color=(255, 255, 255))
    DRAWERS[pattern](img, rng)
    return img


def generate_set(out_dir: Path, count: int, rng: random.Random, size_cycle: bool) -> GenStats:
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = GenStats()
    size_names = list(SIZES.keys())
    for i in range(count):
        if size_cycle:
            # Zestaw origin: równy rozkład small/medium/large po kolei.
            size_name = size_names[i % len(size_names)]
        else:
            size_name = weighted_size_choice(rng)
        pattern = rng.choice(PATTERNS)
        img = generate_image(size_name, pattern, rng)
        filename = f"img_{i:04d}_{size_name}_{pattern}.jpg"
        path = out_dir / filename
        img.save(path, "JPEG", quality=JPEG_QUALITY)
        stats.count += 1
        stats.total_bytes += path.stat().st_size
    return stats


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def main() -> None:
    start = time.monotonic()

    # Dwa niezależne, ale deterministyczne strumienie losowości (seed 42) —
    # osobne instancje random.Random, żeby kolejność generowania jednego
    # zestawu nie wpływała na drugi.
    corpus_rng = random.Random(SEED)
    origin_rng = random.Random(SEED)

    print(f"Generuję korpus deterministyczny (seed={SEED})...")

    corpus_stats = generate_set(CORPUS_DIR, CORPUS_COUNT, corpus_rng, size_cycle=False)
    origin_stats = generate_set(ORIGIN_DIR, ORIGIN_COUNT, origin_rng, size_cycle=True)

    elapsed = time.monotonic() - start

    print()
    print("=== Podsumowanie generowania korpusu ===")
    print(f"  {CORPUS_DIR.relative_to(REPO_ROOT)}: {corpus_stats.count} plików, "
          f"{human_size(corpus_stats.total_bytes)}")
    print(f"  {ORIGIN_DIR.relative_to(REPO_ROOT)}: {origin_stats.count} plików, "
          f"{human_size(origin_stats.total_bytes)}")
    total_count = corpus_stats.count + origin_stats.count
    total_bytes = corpus_stats.total_bytes + origin_stats.total_bytes
    print(f"  RAZEM: {total_count} plików, {human_size(total_bytes)}")
    print(f"  Czas generowania: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
