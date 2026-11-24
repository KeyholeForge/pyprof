"""Upload, thumbnails and image filters — the domain logic of the pixelforge service.

This module WORKS from the start (it is not the topic layer of the course), but
it deliberately contains three performance flaws built in from the beginning:
  - F1 (memory, exercise 08): THUMBNAIL_CACHE grows without bound.
  - F1b (memory, exercise 09): apply_pipeline builds a FilterPipeline on every
    request, and the constructor registers it in the global EVENTS bus.
  - F2 (CPU, exercise 05): the "sepia" filter is computed naively in pure Python.
"""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageFilter, ImageOps

from . import config, pipeline, storage

FILTERS = ("grayscale", "blur", "sepia")

# MEMORY FLAW (F1, exercise 08): a global thumbnail cache in process memory,
# with no size limit, no TTL and no eviction at all (LRU or otherwise). Every new
# (image_id, size) combination adds an entry that is never removed — under
# loadgen traffic (random corpus images × different thumbnail sizes) the
# process RSS grows monotonically. Visible in `memray flamegraph --leaks` as
# unreleased allocations in this module and in GET /debug/memory (exercise 07).
# The fixed version (for example functools.lru_cache with maxsize, or a cache
# with a TTL): there is no separate snippets file — it is discussed in the text
# of exercise 08.
THUMBNAIL_CACHE: dict[tuple[str, int], bytes] = {}


class ImageNotFoundError(Exception):
    """No image with the given ID in local storage."""


class UnknownFilterError(Exception):
    """Unknown filter name."""


# Extensions under which save_upload / fetch_one may save a file.
_KNOWN_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


def _image_path(image_id: str) -> Path:
    """Path of the file with the given ID — O(1): a few `stat()` calls, no `glob` over the directory.

    The file lives at `UPLOAD_DIR/<id><extension>`. We check a few known
    extensions instead of scanning the directory, so the cost does not depend
    on the number of files in `data/uploads/`.
    """
    if not image_id.isalnum():  # the ID is a uuid4 hex — reject `..`, `/` etc.
        raise ImageNotFoundError(image_id)
    for suffix in _KNOWN_SUFFIXES:
        candidate = config.UPLOAD_DIR / f"{image_id}{suffix}"
        if candidate.exists():
            return candidate
    raise ImageNotFoundError(image_id)


async def save_upload(file: UploadFile) -> dict:
    """Saves the uploaded file to local storage and returns its metadata."""
    image_id = uuid.uuid4().hex
    suffix = Path(file.filename or "").suffix or ".jpg"
    dest = config.UPLOAD_DIR / f"{image_id}{suffix}"
    data = await file.read()
    storage.save_bytes(dest, data)
    return {
        "id": image_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(data),
    }


def get_thumbnail(image_id: str, size: int) -> bytes:
    """Returns the image thumbnail (JPEG), generating it if it is not in the cache."""
    cache_key = (image_id, size)
    if cache_key in THUMBNAIL_CACHE:
        return THUMBNAIL_CACHE[cache_key]

    path = _image_path(image_id)
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((size, size))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        data = buf.getvalue()

    THUMBNAIL_CACHE[cache_key] = data  # F1: grows without bound, see above
    return data


def apply_filter(image_id: str, name: str) -> bytes:
    """Applies filter `name` to image `image_id` and returns the result as a JPEG."""
    if name not in FILTERS:
        raise UnknownFilterError(name)

    path = _image_path(image_id)
    with Image.open(path) as img:
        img = img.convert("RGB")
        if name == "grayscale":
            result = ImageOps.grayscale(img).convert("RGB")
        elif name == "blur":
            result = img.filter(ImageFilter.GaussianBlur(radius=4))
        else:  # "sepia" — F2, see _sepia_naive
            result = _sepia_naive(img)

        buf = BytesIO()
        result.save(buf, format="JPEG", quality=85)
        data = buf.getvalue()

    out_path = config.FILTERED_DIR / f"{image_id}_{name}.jpg"
    storage.save_bytes(out_path, data)
    return data


def apply_pipeline(image_id: str, preset: str) -> tuple[bytes, int]:
    """Runs the image through the filter pipeline `preset`; returns (JPEG, number of steps).

    MEMORY FLAW (F1b, exercise 09): the pipeline (a graph of nodes with
    intermediate buffers) is built on EVERY call, and its constructor registers
    it in the global event bus `pipeline.EVENTS`. Nobody unregisters it from
    there, so the graph does not die after the request — subsequent identical
    requests leave more and more live graphs behind. Fixed versions:
    solutions/pipeline_snippets.py.
    """
    path = _image_path(image_id)
    pipe = pipeline.FilterPipeline(preset)  # an expensive graph, built per request
    img = pipeline.load_work_image(path)
    result = pipe.run(img)
    buf = BytesIO()
    result.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), len(pipe.nodes)


def _sepia_naive(img: Image.Image) -> Image.Image:
    """CPU FLAW (F2, exercise 05): the sepia filter computed by hand, pixel by pixel.

    Instead of Pillow's matrix operation (`Image.convert("RGB", matrix=...)`,
    vectorized in C), this function runs a double `for y / for x` loop in pure
    Python and reads/writes every pixel by indexing. For a large corpus image
    (2000x1500 = 3,000,000 pixels) that is millions of interpreter iterations
    per endpoint call.

    In a CPU profile (Pyroscope UI, `py-spy record`) it shows up as a very
    WIDE flame graph frame in this function — the dominant cost of the whole
    request. The fixed, fast version (Pillow, a 3x3 matrix through
    `Image.convert`): solutions/filters_snippets.py (exercise 05).
    """
    width, height = img.size
    out = Image.new("RGB", (width, height))
    src_pixels = img.load()
    dst_pixels = out.load()
    for y in range(height):
        for x in range(width):
            r, g, b = src_pixels[x, y]
            tr = min(255, int(0.393 * r + 0.769 * g + 0.189 * b))
            tg = min(255, int(0.349 * r + 0.686 * g + 0.168 * b))
            tb = min(255, int(0.272 * r + 0.534 * g + 0.131 * b))
            dst_pixels[x, y] = (tr, tg, tb)
    return out
