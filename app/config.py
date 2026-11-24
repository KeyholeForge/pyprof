"""Configuration of the pixelforge application.

The pyprof course does not use an LLM, so there are no secrets worth loading
through python-dotenv (deliberately left out of requirements.txt) - reading
environment variables with sensible defaults, identical to the ones in
`.env.example`, is enough. If you want to override any of them locally, export
it before starting uvicorn, for example:

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

# Profiler sampling mode, chosen ONCE at process start:
# PYROSCOPE_WALL=1 -> wall-clock (oncpu=False, gil_only=False), otherwise CPU.
PYROSCOPE_WALL = os.environ.get("PYROSCOPE_WALL", "0") == "1"

# tracemalloc slows the application down (measured: the sepia filter is ~11x
# slower, because every allocation is tracked), so it is OFF by default.
# PIXELFORGE_TRACEMALLOC=1 turns it on from process start; otherwise it starts
# on the first GET /debug/memory.
TRACEMALLOC = os.environ.get("PIXELFORGE_TRACEMALLOC", "0") == "1"

ORIGIN_BASE_URL = os.environ.get("ORIGIN_BASE_URL", "http://127.0.0.1:8041")

CORPUS_DIR = REPO_ROOT / os.environ.get("CORPUS_DIR", "data/corpus")
ORIGIN_IMAGES_DIR = REPO_ROOT / os.environ.get("ORIGIN_IMAGES_DIR", "data/origin_images")

# The application's runtime storage (upload/fetch/filters) - NOT the course's
# data corpus. Created at startup if it does not exist. It is not part of
# .env.example, because it is an implementation detail, not a course
# configuration parameter.
UPLOAD_DIR = REPO_ROOT / "data" / "uploads"
FILTERED_DIR = UPLOAD_DIR / "filtered"
