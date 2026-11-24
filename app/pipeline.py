"""The filter pipeline (a graph of nodes) and the event bus — pixelforge domain logic.

This module WORKS from the start, but together with `app/images.py`
(`apply_pipeline`) it contains flaw F1b (exercise 09) — a TRUE memory leak:

  - `FilterPipeline` is a graph of filter nodes, each with its own intermediate buffer;
  - the constructor registers the pipeline in the global `EVENTS` bus
    (`EVENTS.subscribe(self.on_progress)`) — a bound method holds `self`;
  - nothing ever calls `unsubscribe`.

If the pipeline is built on EVERY request (which is what `images.apply_pipeline`
does), every request leaves a live graph behind, buffers included, and the bus
delivers every event to an ever longer list of subscribers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import count

from PIL import Image, ImageFilter, ImageOps

# Side of the working image: the pipeline works on a thumbnail, not on the original.
WORK_SIZE = 64


class EventBus:
    """A simple event bus: a list of subscribers called synchronously."""

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


# The process-wide bus — lives as long as the process does.
EVENTS = EventBus()


class Metrics:
    """Event counters — registered ONCE, so it is not a flaw."""

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
    "sketch": ("grayscale", "blur", "contrast"),
    "poster": ("poster", "sharpen", "contrast"),
}


class UnknownPresetError(Exception):
    """Unknown pipeline preset name."""


@dataclass
class FilterNode:
    """A graph node: a filter + its last intermediate result (a preview for debugging)."""

    name: str
    func: Callable[[Image.Image], Image.Image]
    last_output: bytes = b""


_pipeline_ids = count(1)


class FilterPipeline:
    """A graph of filter nodes. Building it is expensive (nodes, buffers), and
    the constructor registers the pipeline in the global event bus."""

    def __init__(self, preset: str) -> None:
        if preset not in PRESETS:
            raise UnknownPresetError(preset)
        self.preset = preset
        self.pipeline_id = next(_pipeline_ids)
        self.nodes = [FilterNode(name, NODE_FUNCS[name]) for name in PRESETS[preset]]
        self.steps_seen = 0
        EVENTS.subscribe(self.on_progress)  # a bound method holds `self`

    def on_progress(self, event: dict) -> None:
        if event["pipeline_id"] == self.pipeline_id:
            self.steps_seen += 1

    def close(self) -> None:
        """Unregisters the pipeline from the bus (a local fix: call it in `finally`)."""
        EVENTS.unsubscribe(self.on_progress)

    def run(self, img: Image.Image) -> Image.Image:
        for step, node in enumerate(self.nodes, start=1):
            img = node.func(img)
            node.last_output = img.tobytes()  # the node's intermediate result
            EVENTS.publish(
                {"pipeline_id": self.pipeline_id, "node": node.name, "step": step, "of": len(self.nodes)}
            )
        return img


def load_work_image(path) -> Image.Image:
    """Loads an image and shrinks it to WORK_SIZE (JPEG: draft speeds up decoding)."""
    with Image.open(path) as src:
        src.draft("RGB", (WORK_SIZE, WORK_SIZE))
        img = src.convert("RGB")
    img.thumbnail((WORK_SIZE, WORK_SIZE))
    return img
