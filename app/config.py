"""Konfiguracja aplikacji pixelforge.

Kurs pyprof nie używa LLM, więc nie ma sekretów wartych ładowania przez
python-dotenv (celowo pominięty w requirements.txt) — wystarczy odczyt
zmiennych środowiskowych z sensownymi domyślnymi wartościami, identycznymi
jak w `.env.example`. Jeśli chcesz nadpisać którąś z nich lokalnie, wyeksportuj
ją przed uruchomieniem uvicorna, np.:

    export PIXELFORGE_PORT=8040
    uvicorn app.main:app --port "$PIXELFORGE_PORT"
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PIXELFORGE_PORT = int(os.environ.get("PIXELFORGE_PORT", "8040"))

PYROSCOPE_SERVER_ADDRESS = os.environ.get(
    "PYROSCOPE_SERVER_ADDRESS", "http://127.0.0.1:4040"
)
PYROSCOPE_APPLICATION_NAME = os.environ.get(
    "PYROSCOPE_APPLICATION_NAME", "pixelforge"
)

# Tryb próbkowania profilera, wybierany RAZ przy starcie procesu:
# PYROSCOPE_WALL=1 → wall-clock (oncpu=False, gil_only=False), inaczej CPU.
PYROSCOPE_WALL = os.environ.get("PYROSCOPE_WALL", "0") == "1"

# tracemalloc spowalnia aplikację (pomiar: filtr sepia ~11x wolniejszy, bo każda
# alokacja jest śledzona), więc domyślnie jest WYŁĄCZONE. PIXELFORGE_TRACEMALLOC=1
# włącza je od startu procesu; inaczej startuje przy pierwszym GET /debug/memory.
TRACEMALLOC = os.environ.get("PIXELFORGE_TRACEMALLOC", "0") == "1"

ORIGIN_BASE_URL = os.environ.get("ORIGIN_BASE_URL", "http://127.0.0.1:8041")

CORPUS_DIR = REPO_ROOT / os.environ.get("CORPUS_DIR", "data/corpus")
ORIGIN_IMAGES_DIR = REPO_ROOT / os.environ.get("ORIGIN_IMAGES_DIR", "data/origin_images")

# Storage runtime aplikacji (upload/fetch/filtry) — NIE korpus danych kursu.
# Tworzony przy starcie, jeśli nie istnieje. Nie jest częścią .env.example,
# bo to szczegół implementacyjny, nie parametr konfiguracyjny kursu.
UPLOAD_DIR = REPO_ROOT / "data" / "uploads"
FILTERED_DIR = UPLOAD_DIR / "filtered"
