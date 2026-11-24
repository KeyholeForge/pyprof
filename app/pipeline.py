"""Potok filtrów (graf węzłów) i szyna zdarzeń — logika domenowa pixelforge.

Ten moduł DZIAŁA od startu, ale razem z `app/images.py` (`apply_pipeline`)
zawiera wadę W1b (ćwiczenie 09) — PRAWDZIWY wyciek pamięci:

  - `FilterPipeline` to graf węzłów filtrów, każdy ze swoim buforem pośrednim;
  - konstruktor rejestruje potok w globalnej szynie `EVENTS`
    (`EVENTS.subscribe(self.on_progress)`) — metoda związana trzyma `self`;
  - nic nigdy nie woła `unsubscribe`.

Jeśli potok jest budowany przy KAŻDYM żądaniu (tak robi `images.apply_pipeline`),
każde żądanie zostawia po sobie żywy graf razem z buforami, a szyna rozsyła
każde zdarzenie do coraz dłuższej listy nasłuchujących.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import count

from PIL import Image, ImageFilter, ImageOps

# Bok obrazu roboczego: potok pracuje na miniaturze, nie na oryginale.
WORK_SIZE = 64


class EventBus:
    """Prosta szyna zdarzeń: lista nasłuchujących wołanych synchronicznie."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[dict], None]] = []

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict], None]) -> None:
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass

    def publish(self, event: dict) -> None:
        for callback in list(self._subscribers):
            callback(event)

    def __len__(self) -> int:
        return len(self._subscribers)


# Globalna szyna procesu — żyje tak długo, jak proces.
EVENTS = EventBus()


class Metrics:
    """Liczniki zdarzeń — rejestrowany JEDEN raz, więc nie jest wadą."""

    def __init__(self) -> None:
        self.steps = 0

    def on_event(self, event: dict) -> None:
        self.steps += 1


METRICS = Metrics()
EVENTS.subscribe(METRICS.on_event)


def _grayscale(img: Image.Image) -> Image.Image:
    return ImageOps.grayscale(img).convert("RGB")


def _blur(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=2))


def _contrast(img: Image.Image) -> Image.Image:
    return ImageOps.autocontrast(img)


def _poster(img: Image.Image) -> Image.Image:
    return ImageOps.posterize(img, 3)


def _sharpen(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.SHARPEN)


NODE_FUNCS = {
    "grayscale": _grayscale,
    "blur": _blur,
    "contrast": _contrast,
    "poster": _poster,
    "sharpen": _sharpen,
}

PRESETS = {
    "szkic": ("grayscale", "blur", "contrast"),
    "plakat": ("poster", "sharpen", "contrast"),
}


class UnknownPresetError(Exception):
    """Nieznana nazwa presetu potoku."""


@dataclass
class FilterNode:
    """Węzeł grafu: filtr + ostatni wynik pośredni (podgląd do debugowania)."""

    name: str
    func: Callable[[Image.Image], Image.Image]
    last_output: bytes = b""


_pipeline_ids = count(1)


class FilterPipeline:
    """Graf węzłów filtrów. Zbudowanie go jest drogie (węzły, bufory), a
    konstruktor rejestruje potok w globalnej szynie zdarzeń."""

    def __init__(self, preset: str) -> None:
        if preset not in PRESETS:
            raise UnknownPresetError(preset)
        self.preset = preset
        self.pipeline_id = next(_pipeline_ids)
        self.nodes = [FilterNode(name, NODE_FUNCS[name]) for name in PRESETS[preset]]
        self.steps_seen = 0
        EVENTS.subscribe(self.on_progress)  # metoda związana trzyma `self`

    def on_progress(self, event: dict) -> None:
        if event["pipeline_id"] == self.pipeline_id:
            self.steps_seen += 1

    def close(self) -> None:
        """Wyrejestrowuje potok z szyny (naprawa lokalna: wołaj w `finally`)."""
        EVENTS.unsubscribe(self.on_progress)

    def run(self, img: Image.Image) -> Image.Image:
        for step, node in enumerate(self.nodes, start=1):
            img = node.func(img)
            node.last_output = img.tobytes()  # wynik pośredni węzła
            EVENTS.publish(
                {"pipeline_id": self.pipeline_id, "node": node.name, "step": step, "of": len(self.nodes)}
            )
        return img


def load_work_image(path) -> Image.Image:
    """Wczytuje obraz i zmniejsza do WORK_SIZE (JPEG: draft przyspiesza dekodowanie)."""
    with Image.open(path) as src:
        src.draft("RGB", (WORK_SIZE, WORK_SIZE))
        img = src.convert("RGB")
    img.thumbnail((WORK_SIZE, WORK_SIZE))
    return img
