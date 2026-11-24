"""app/main.py — serwis HTTP pixelforge (FastAPI).

Wiąże moduły domenowe (images, fetch, reports, storage) z warstwą-tematem
kursu (profiling). Wszystkie endpointy domenowe działają od startu, niezależnie
od stanu app/profiling.py. Jedyne endpointy zależne od profiling.py to
GET /debug/memory — dopóki odpowiednie funkcje
w profiling.py nie są zaimplementowane, zwracają HTTP 501 z podpowiedzią.

Tryb profilera (CPU albo wall-clock) wybiera zmienna PYROSCOPE_WALL=1 przy starcie
procesu; GET /health raportuje stan profilowania.
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

# uvicorn konfiguruje tylko własne loggery; bez tego komunikaty INFO aplikacji
# (np. „Profiling aktywne") nie trafiałyby nigdzie.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
logger = logging.getLogger("pixelforge")

STARTED_AT = time.time()  # epoka startu procesu — check.py pyta Pyroscope tylko o próbki od tej chwili


@contextmanager
def _instrumented(tags: dict[str, str]) -> Iterator[None]:
    """Otacza blok kodu tag_wrapperem z profiling.py, jeśli ćwiczenie 04 jest
    już zrobione; w przeciwnym razie działa jako no-op. Dzięki temu endpointy
    domenowe NIE zależą od stanu warstwy-tematu — profilowanie jest czystym
    dodatkiem, nie wymaganiem do działania aplikacji.
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
            "Profiling aktywne (Pyroscope: %s, tryb: %s)",
            config.PYROSCOPE_SERVER_ADDRESS,
            "wall" if config.PYROSCOPE_WALL else "cpu",
        )
    except NotImplementedError:
        logger.warning(
            "Profiling nieaktywne — zobacz ćwiczenie 01: app/profiling.py "
            "(init_profiling niezaimplementowane). Reszta aplikacji działa normalnie."
        )
    if config.TRACEMALLOC:
        try:
            profiling.start_memory_tracking()
        except NotImplementedError:
            logger.info("Śledzenie pamięci nieaktywne — zobacz ćwiczenie 07.")
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
            raise HTTPException(status_code=404, detail=f"Nie znaleziono obrazu: {image_id}")
        return Response(content=data, media_type="image/jpeg")


@app.get("/images/{image_id}/filter/{name}")
def get_filtered(image_id: str, name: str) -> Response:
    with _instrumented({"endpoint": "filter", "filter": name}):
        try:
            data = images.apply_filter(image_id, name)
        except images.ImageNotFoundError:
            raise HTTPException(status_code=404, detail=f"Nie znaleziono obrazu: {image_id}")
        except images.UnknownFilterError:
            raise HTTPException(
                status_code=400,
                detail=f"Nieznany filtr: {name!r}. Dostępne: {', '.join(images.FILTERS)}",
            )
        return Response(content=data, media_type="image/jpeg")


@app.get("/images/{image_id}/pipeline/{preset}")
def get_pipeline(image_id: str, preset: str) -> Response:
    with _instrumented({"endpoint": "pipeline", "preset": preset}):
        try:
            data, steps = images.apply_pipeline(image_id, preset)
        except images.ImageNotFoundError:
            raise HTTPException(status_code=404, detail=f"Nie znaleziono obrazu: {image_id}")
        except pipeline.UnknownPresetError:
            raise HTTPException(
                status_code=400,
                detail=f"Nieznany preset: {preset!r}. Dostępne: {', '.join(pipeline.PRESETS)}",
            )
        return Response(content=data, media_type="image/jpeg", headers={"X-Pipeline-Steps": str(steps)})


@app.post("/images/fetch", status_code=201)
async def fetch_image(body: FetchRequest) -> dict:
    with _instrumented({"endpoint": "fetch"}):
        try:
            return await fetch.fetch_one(body.url)
        except Exception as exc:  # httpx.HTTPError i pochodne
            raise HTTPException(status_code=502, detail=f"Nie udało się pobrać {body.url}: {exc}")


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
                "tracemalloc dopiero wystartowało (albo nie było jeszcze alokacji) — "
                "wygeneruj ruch i wywołaj ponownie. Start od razu: PIXELFORGE_TRACEMALLOC=1."
            )
        return body
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail=f"Profilowanie pamięci nieaktywne — zobacz ćwiczenie 07: app/profiling.py ({exc})",
        )


@app.get("/debug/objects")
def debug_objects() -> dict:
    """Liczniki żywych obiektów — działa bez tracemalloc (ćwiczenie 09)."""
    live = sum(1 for o in gc.get_objects() if type(o) is pipeline.FilterPipeline)
    t0 = time.perf_counter()
    for _ in range(20):  # puste zdarzenie: koszt rozesłania do wszystkich nasłuchujących
        pipeline.EVENTS.publish({"pipeline_id": 0})
    publish_us = (time.perf_counter() - t0) / 20 * 1e6
    return {
        "publish_us": round(publish_us, 1),
        "live_pipelines": live,
        "event_subscribers": len(pipeline.EVENTS),
        "pipeline_steps_total": pipeline.METRICS.steps,
    }
