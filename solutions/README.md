# solutions/ — module → exercise mapping

This directory contains COMPLETE, WORKING versions of the code whose skeleton
(with `TODO`) the learner gets in `app/`. The only module with a skeleton is
`app/profiling.py` — the rest of `app/` (images.py, fetch.py, reports.py,
storage.py, main.py) works from the start and is NOT duplicated here as
cumulative versions; the `*_snippets.py` files show only the fragments to
introduce in a specific exercise (fixing a flaw or — in the case of exercise
09 — deliberately introducing and fixing one).

## app/profiling.py (topic layer) — cumulative versions

| File                            | Unlocks                                       | Exercise |
|----------------------------------|------------------------------------------------|-----------|
| `ex01_profiling.py`             | `init_profiling()` (pyroscope.configure; the `wall` parameter is accepted and ignored for now) | 01 |
| `ex04_profiling.py`             | + `tag_wrapper()` (per-endpoint tagging)       | 04        |
| `ex07_profiling.py`             | + `start_memory_tracking()`/`get_memory_snapshot()` (tracemalloc) | 07 |
| `ex11_profiling.py`             | + wall mode in `init_profiling` (`oncpu=not wall`, `gil_only=not wall`, tag `mode`) | 11 |
| `exFINAL_profiling.py`          | everything at once (identical to ex11)         | 16 / final|

Usage: `cp solutions/exNN_profiling.py app/profiling.py`, restart uvicorn.
Each subsequent file is a superset of the previous one — functions from future
exercises still have `TODO`/`NotImplementedError`, so copying e.g.
`ex04_profiling.py` gives exactly the state of knowledge the learner should have
after exercise 04, no more.

The sampling mode (cpu or wall-clock) is chosen **once, at process startup**:
`PYROSCOPE_WALL=1 uvicorn app.main:app --host 127.0.0.1 --port 8040`.
On `pyroscope-io` 1.4.0, calling `pyroscope.configure()` again while the agent
is running is refused and changes neither the mode nor the tags — that is why
there is no on-the-fly switch and no `/debug/profiling/mode` endpoint.

The `tag_wrapper` signature: `pyroscope.tag_wrapper(tags: dict)` — a context
manager that takes ONE argument, a dictionary of tags. It sets the tags on the
**thread**, so in `async def` handlers (the shared event loop thread) the tags of
concurrent requests get mixed up (exercise 11, `11a`). Our `profiling.tag_wrapper`
has an identical signature and simply delegates to the library, so that
`app/main.py` has a stable API.

## Snippets and scripts (flaw fixes, demonstrations)

| File                        | What it does                                           | Exercise |
|------------------------------|---------------------------------------------------------|-----------|
| `profile_sepia.py`          | a cProfile script for `_sepia_naive` (writes `profiles/ex03_sepia.prof`) | 03 |
| `filters_snippets.py`       | F2 (CPU) — sepia via `Image.convert(matrix=...)` instead of a Python loop | 05 |
| `images_snippets.py`        | F1 (memory) — the thumbnail cache as an LRU (`OrderedDict`, limit 200) | 08 |
| `pipeline_snippets.py`      | F1b (true leak) — A: a shared graph (main), B: `unsubscribe` in `finally`, C: `WeakEventBus`; the "who holds it" script (`gc.get_referrers`) | 09 |
| `reports_snippets.py`       | F7 — the `+=` and `join` versions of the report (+ measurement results; the difference in the service is negligible) | 09 (★ Bonus B) |
| `gil_demo.py`               | a GIL demonstration: `sequential` / `threads N` / `processes N` (constant work) | 10 |
| `fetch_snippets.py`         | F3a+F3b (TCP) — a shared `httpx.AsyncClient` (`fetch_one(client, url)`) + `asyncio.gather` | 12-13 |
| `storage_snippets.py`       | F4 (disk) — a buffer + a single write/fsync instead of fsync after every chunk | 14 |

These files are NOT meant to replace a whole module 1:1 (like
`exNN_profiling.py`) — they are fragments/functions to move by hand, because they
touch single functions in larger files (sometimes two files at once, like
`fetch_snippets.py`, which changes both `main.py` and `fetch.py`).

## Flaws in the course (registry)

Built into `app/` from the start:
- **F1** (memory, ex. 07-08): `THUMBNAIL_CACHE` in `app/images.py` — a global
  dict with no eviction → `images_snippets.py`.
- **F1b** (memory — a true leak, ex. 09): a `FilterPipeline` built in
  `images.apply_pipeline` on every request and registered in the global event bus
  `pipeline.EVENTS` (`app/pipeline.py`) → `pipeline_snippets.py`. The endpoint
  `GET /images/{id}/pipeline/{preset}`, counters in `GET /debug/objects`, traffic
  `loadgen.py --scenario pipeline` (option `--requests N`).
- **F2** (CPU, ex. 03/05/06): `_sepia_naive` in `app/images.py` → `filters_snippets.py`.
- **F3** (TCP, ex. 12-13): `app/fetch.py` (a client per request, fan-out in a loop) →
  `fetch_snippets.py`.
- **F4** (disk, ex. 14; tied to ex. 11): `app/storage.py` → `storage_snippets.py`.

Introduced by instruction / demonstrations:
- **F5** (GIL, ex. 10): `gil_demo.py` — threads for CPU-bound work instead of
  processes; a standalone demonstration, no changes in `app/`.
- **F6** (sync-in-async, ex. 11): a blocking call in `fetch_image` — introduced and
  removed in the text of the exercise; in the final (ex. 16) as an occasional blocking.
- **F7** (string concatenation, ex. 09 ★ Bonus B): in the service this is a
  micro-optimization **with no measurable effect** (a lesson about measuring before
  optimizing); the `app/reports.py` code uses `join`. `reports_snippets.py` has both
  versions and the measurement results.
- **F8** (a regression between versions, ex. 15): reverting the F2 fix and the `version`
  tag in the text of the exercise; no separate code file.

The final (ex. 16): F1 + F2 + F3 (a+b) + F6 (occasional blocking); F4 fixed.
The key with numbers: `ex16_answers.md`. Questions and answers: `review_questions_answers.md`;
graduated hints: `hints/`; the skills map and audience variants: `todo.md`.
