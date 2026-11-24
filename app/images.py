"""Upload, miniatury i filtry obrazów — logika domenowa serwisu pixelforge.

Ten moduł DZIAŁA od startu (nie jest warstwą-tematem kursu), ale celowo
zawiera trzy wady wydajnościowe wszyte od początku:
  - W1 (pamięć, ćwiczenie 08): THUMBNAIL_CACHE rośnie bez ograniczeń.
  - W1b (pamięć, ćwiczenie 09): apply_pipeline buduje FilterPipeline przy
    każdym żądaniu, a konstruktor rejestruje go w globalnej szynie EVENTS.
  - W2 (CPU, ćwiczenie 05): filtr "sepia" liczony naiwnie w czystym Pythonie.
"""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageFilter, ImageOps

from . import config, pipeline, storage

FILTERS = ("grayscale", "blur", "sepia")

# WADA PAMIĘCIOWA (W1, ćwiczenie 08): globalny cache miniatur w pamięci procesu,
# bez limitu rozmiaru, bez TTL, bez żadnej evikcji (LRU czy inne). Każda nowa
# kombinacja (image_id, size) dokłada wpis, który nigdy nie jest usuwany — pod
# obciążeniem loadgenu (losowe obrazy z korpusu × różne rozmiary miniatur) RSS
# procesu rośnie monotonicznie. Widoczne w `memray flamegraph --leaks` jako
# nieuwolnione alokacje w tym module oraz w GET /debug/memory (ćwiczenie 07).
# Naprawiona wersja (np. functools.lru_cache z maxsize, albo cache z TTL):
# nie ma osobnego pliku fragmentów — omówiona w treści ćwiczenia 08.
THUMBNAIL_CACHE: dict[tuple[str, int], bytes] = {}


class ImageNotFoundError(Exception):
    """Brak obrazu o podanym ID w lokalnym storage."""


class UnknownFilterError(Exception):
    """Nieznana nazwa filtra."""


# Rozszerzenia, pod którymi save_upload / fetch_one mogą zapisać plik.
_KNOWN_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


def _image_path(image_id: str) -> Path:
    """Ścieżka pliku o danym ID — O(1): kilka `stat()`, bez `glob` po katalogu.

    Plik leży w `UPLOAD_DIR/<id><rozszerzenie>`. Sprawdzamy kilka znanych
    rozszerzeń zamiast przeszukiwać katalog, więc koszt nie zależy od liczby
    plików w `data/uploads/`.
    """
    if not image_id.isalnum():  # ID to hex z uuid4 — odrzuć `..`, `/` itp.
        raise ImageNotFoundError(image_id)
    for suffix in _KNOWN_SUFFIXES:
        candidate = config.UPLOAD_DIR / f"{image_id}{suffix}"
        if candidate.exists():
            return candidate
    raise ImageNotFoundError(image_id)


async def save_upload(file: UploadFile) -> dict:
    """Zapisuje przesłany plik do lokalnego storage i zwraca metadane."""
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
    """Zwraca miniaturę obrazu (JPEG), generując ją jeśli nie ma w cache."""
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

    THUMBNAIL_CACHE[cache_key] = data  # W1: rośnie bez ograniczeń, zobacz wyżej
    return data


def apply_filter(image_id: str, name: str) -> bytes:
    """Nakłada filtr `name` na obraz `image_id` i zwraca wynik jako JPEG."""
    if name not in FILTERS:
        raise UnknownFilterError(name)

    path = _image_path(image_id)
    with Image.open(path) as img:
        img = img.convert("RGB")
        if name == "grayscale":
            result = ImageOps.grayscale(img).convert("RGB")
        elif name == "blur":
            result = img.filter(ImageFilter.GaussianBlur(radius=4))
        else:  # "sepia" — W2, patrz _sepia_naive
            result = _sepia_naive(img)

        buf = BytesIO()
        result.save(buf, format="JPEG", quality=85)
        data = buf.getvalue()

    out_path = config.FILTERED_DIR / f"{image_id}_{name}.jpg"
    storage.save_bytes(out_path, data)
    return data


def apply_pipeline(image_id: str, preset: str) -> tuple[bytes, int]:
    """Przepuszcza obraz przez potok filtrów `preset`; zwraca (JPEG, liczba kroków).

    WADA PAMIĘCI (W1b, ćwiczenie 09): potok (graf węzłów z buforami pośrednimi)
    jest budowany przy KAŻDYM wywołaniu, a jego konstruktor rejestruje go w
    globalnej szynie zdarzeń `pipeline.EVENTS`. Nikt go stamtąd nie wyrejestrowuje,
    więc po żądaniu graf nie umiera — kolejne identyczne żądania zostawiają
    kolejne żywe grafy. Wersje naprawione: solutions/pipeline_fragmenty.py.
    """
    path = _image_path(image_id)
    pipe = pipeline.FilterPipeline(preset)  # drogi graf, budowany per żądanie
    img = pipeline.load_work_image(path)
    result = pipe.run(img)
    buf = BytesIO()
    result.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), len(pipe.nodes)


def _sepia_naive(img: Image.Image) -> Image.Image:
    """WADA CPU (W2, ćwiczenie 05): filtr sepia liczony ręcznie, piksel po pikselu.

    Zamiast operacji macierzowej Pillow (`Image.convert("RGB", matrix=...)`,
    zwektoryzowanej w C), ta funkcja robi podwójną pętlę `for y / for x`
    w czystym Pythonie i czyta/zapisuje każdy piksel przez indeksowanie. Dla dużego
    obrazu z korpusu (2000x1500 = 3 000 000 pikseli) to miliony iteracji
    interpretera na jedno wywołanie endpointu.

    W profilu CPU (Pyroscope UI, `py-spy record`) widać to jako bardzo
    SZEROKĄ ramę flamegrafu w tej funkcji — dominujący koszt całego requestu.
    Naprawiona, szybka wersja (Pillow, macierz 3x3 przez `Image.convert`):
    solutions/filters_fragmenty.py (ćwiczenie 05).
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
