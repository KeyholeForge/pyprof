"""app/main.py — the pixelforge HTTP service (FastAPI).

Ties the domain modules (images, fetch, reports, storage) to the topic layer
of the course (profiling). All domain endpoints work from the start,
regardless of the state of app/profiling.py. The only endpoint that depends
on profiling.py is GET /debug/memory — until the relevant functions
in profiling.py are implemented, it returns HTTP 501 with a hint.

The profiler mode (CPU or wall-clock) is chosen by the PYROSCOPE_WALL=1 variable at
process start; GET /health reports the profiling state.
"""

from __future__ import annotations

import gc
import logging
import os
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Iterator

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from . import config, fetch, images, pipeline, profiling, reports

# uvicorn configures only its own loggers; without this, the application's INFO
# messages (for example "Profiling active") would go nowhere.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
logger = logging.getLogger("pixelforge")

STARTED_AT = time.time()  # the process start epoch — check.py asks Pyroscope only for samples since this moment


@contextmanager
def _instrumented(tags: dict[str, str]) -> Iterator[None]:
    """Wraps a block of code in tag_wrapper from profiling.py if exercise 04 is
    already done; otherwise it acts as a no-op. Thanks to this, the domain
    endpoints do NOT depend on the state of the topic layer — profiling is a
    pure add-on, not a requirement for the application to work.
    """
    try:
        with profiling.tag_wrapper(tags):
            yield
    except NotImplementedError:
        yield


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        profiling.init_profiling(
            app_name=config.PYROSCOPE_APPLICATION_NAME,
            server_address=config.PYROSCOPE_SERVER_ADDRESS,
            tags={"service": "pixelforge"},
            wall=config.PYROSCOPE_WALL,
        )
        logger.info(
            "Profiling active (Pyroscope: %s, mode: %s)",
            config.PYROSCOPE_SERVER_ADDRESS,
            "wall" if config.PYROSCOPE_WALL else "cpu",
        )
    except NotImplementedError:
        logger.warning(
            "Profiling inactive — see exercise 01: app/profiling.py "
            "(init_profiling not implemented). The rest of the application works normally."
        )
    if config.TRACEMALLOC:
        try:
            profiling.start_memory_tracking()
        except NotImplementedError:
            logger.info("Memory tracking inactive — see exercise 07.")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config.FILTERED_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="pixelforge", lifespan=lifespan)


class FetchRequest(BaseModel):
    url: str


class FetchBatchRequest(BaseModel):
    urls: list[str]


class ReportsBatchRequest(BaseModel):
    ids: list[str]


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "pid": os.getpid(),
        "started_at": STARTED_AT,
        "profiling": profiling.status(),
    }


@app.post("/images", status_code=201)
async def upload_image(file: UploadFile = File(...)) -> dict:
    with _instrumented({"endpoint": "upload"}):
        return await images.save_upload(file)


@app.get("/images/{image_id}/thumbnail")
def get_thumbnail(image_id: str, size: int = 128) -> Response:
    with _instrumented({"endpoint": "thumbnail", "size": str(size)}):
        try:
            data = images.get_thumbnail(image_id, size)
        except images.ImageNotFoundError:
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
        return Response(content=data, media_type="image/jpeg")


@app.get("/images/{image_id}/filter/{name}")
def get_filtered(image_id: str, name: str) -> Response:
    with _instrumented({"endpoint": "filter", "filter": name}):
        try:
            data = images.apply_filter(image_id, name)
        except images.ImageNotFoundError:
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
        except images.UnknownFilterError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown filter: {name!r}. Available: {', '.join(images.FILTERS)}",
            )
        return Response(content=data, media_type="image/jpeg")


@app.get("/images/{image_id}/pipeline/{preset}")
def get_pipeline(image_id: str, preset: str) -> Response:
    with _instrumented({"endpoint": "pipeline", "preset": preset}):
        try:
            data, steps = images.apply_pipeline(image_id, preset)
        except images.ImageNotFoundError:
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
        except pipeline.UnknownPresetError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown preset: {preset!r}. Available: {', '.join(pipeline.PRESETS)}",
            )
        return Response(content=data, media_type="image/jpeg", headers={"X-Pipeline-Steps": str(steps)})


@app.post("/images/fetch", status_code=201)
async def fetch_image(body: FetchRequest) -> dict:
    with _instrumented({"endpoint": "fetch"}):
        try:
            return await fetch.fetch_one(body.url)
        except Exception as exc:  # httpx.HTTPError and subclasses
            raise HTTPException(status_code=502, detail=f"Failed to fetch {body.url}: {exc}")


@app.post("/images/fetch-batch", status_code=201)
async def fetch_images_batch(body: FetchBatchRequest) -> dict:
    with _instrumented({"endpoint": "fetch-batch", "count": str(len(body.urls))}):
        results = await fetch.fetch_batch(body.urls)
        return {"results": results}


@app.post("/reports/batch")
def reports_batch(body: ReportsBatchRequest) -> Response:
    with _instrumented({"endpoint": "reports-batch", "count": str(len(body.ids))}):
        csv_text = reports.generate_batch_report(body.ids)
        return Response(content=csv_text, media_type="text/csv")


@app.get("/debug/memory")
def debug_memory(top_n: int = 10) -> dict:
    try:
        top = profiling.get_memory_snapshot(top_n)
        body: dict = {"top_allocations": top}
        if not top:
            body["note"] = (
                "tracemalloc has only just started (or there have been no allocations yet) — "
                "generate traffic and call again. To start it right away: PIXELFORGE_TRACEMALLOC=1."
            )
        return body
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail=f"Memory profiling inactive — see exercise 07: app/profiling.py ({exc})",
        )


@app.get("/debug/objects")
def debug_objects() -> dict:
    """Live-object counters — works without tracemalloc (exercise 09)."""
    live = sum(1 for o in gc.get_objects() if type(o) is pipeline.FilterPipeline)
    t0 = time.perf_counter()
    for _ in range(20):  # an empty event: the cost of delivering it to all subscribers
        pipeline.EVENTS.publish({"pipeline_id": 0})
    publish_us = (time.perf_counter() - t0) / 20 * 1e6
    return {
        "publish_us": round(publish_us, 1),
        "live_pipelines": live,
        "event_subscribers": len(pipeline.EVENTS),
        "pipeline_steps_total": pipeline.METRICS.steps,
    }
