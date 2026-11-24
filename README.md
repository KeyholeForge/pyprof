# The pyprof course — profiling Python applications, using pixelforge as the example

> **Language versions:** this branch (`main`) contains the English course.
> The Polish version is on the [`polish`](https://github.com/KeyholeForge/pyprof/tree/polish) branch.
> To switch a local checkout to Polish, run `git switch polish`.

A hands-on "learn-by-doing" course: you build the skill of profiling a FastAPI
application (`pixelforge` — an image-processing service) and watch the effects
in Grafana Pyroscope. You learn by doing — the profiling layer
(`app/profiling.py`) starts unfinished, and building it is the content of
exercises 1, 4, 7 and 11. The rest of the application (upload, thumbnails,
filters, fetching from a URL, reports) works from the first run — your job is
to DIAGNOSE and FIX it, not to write it from scratch. The instructions are in
English.

> **Original Polish version verified 2026-11** on: macOS (Docker Desktop),
> Python 3.14.10 (the application also ran on 3.11), fastapi 0.162.0,
> starlette 1.10.0, uvicorn 0.54.0, httpx 0.28.1, pillow 13.0.0, memray 1.20.0,
> py-spy 0.4.2, pyroscope-io 1.4.0, snakeviz 2.2.2, grafana/pyroscope 2.4.2,
> nginx 1.30 (origin), alpine 3.24. The numbers in the exercises come from a
> single machine (14 cores) — they are orders of magnitude and ratios, not
> values to reproduce to the millisecond. This verification covers the original
> Polish version.
>
> **English edition verified 2026-11-17** from a fresh clone of the `english`
> branch on macOS (Docker Desktop, 15.6 GiB), **Python 3.11.17** (the minimum
> supported version; the Python 3.14 walk-through was done earlier during the
> translation), same pinned package and image versions as above. Result: the
> generated corpus is byte-identical to the original (340 files, SHA-256), the
> unfinished skeleton fails all 16 checks without errors, the reference
> solutions pass `check.py --all` 16/16 twice, and the skeleton fails 16/16
> again after restoring it with a clean profile window. Limits: one machine
> (macOS, not Linux), no `sudo`; the exercise 2 and 10 py-spy steps ran in a
> Linux container with `SYS_PTRACE`, as the README describes; the optional
> free-threaded `3.14t` step of exercise 10 also ran (3.06 s with 4 threads).

The emphasis is on theory and clear explanations of concepts — start with
`exercises/00-theory.md`, read `exercises/NNa-*.md` before the blocks, and look
up definitions in `exercises/glossary.md`.

## Prerequisites

- **Python 3.11–3.14, standard build with the GIL.** The `3.14t` version
  (free-threaded) is ruled out: `pyroscope-io` does not install on it. Check
  your interpreter:
  `python3.14 -c "import sysconfig; print(sysconfig.get_config_var('Py_GIL_DISABLED'))"`
  should print `0` (or `None`). Note: `uv venv --python 3.14` may pick the
  free-threaded build — use `python3.14 -m venv` or check the result with the
  command above.
- Python basics (functions, classes, `async`/`await` at the "I can read and
  understand it" level — you do not need to be able to write advanced asyncio
  from scratch).
- The ability to run `docker compose up -d` and read container logs.
- HTTP basics (what GET/POST and a status code are) — the course does NOT
  assume prior knowledge of profiling, the GIL, the event loop or any of the
  tools used in the course (Pyroscope/py-spy/memray/cProfile) — the course
  teaches them from scratch.
- Docker with at least ~1 GB of free RAM for Pyroscope + origin. No API keys —
  the course uses no LLM or cloud service.

## Architecture

```
   loadgen ──HTTP──▶  pixelforge (locally, 127.0.0.1:8040)
                          │  topic layer: app/profiling.py (built in ex. 1/4/7/11)
                          │  domain: upload/thumbnails/filters/fetch/reports (app/*.py)
                          │  storage: data/uploads/ (runtime), data/corpus/ (corpus)
                          ├──telemetry (CPU or wall-clock)──▶ Pyroscope (UI :4040)
                          └──HTTP (image downloads)──▶ origin (nginx, Docker, :8041)
```

`origin` is an nginx with HTTP/1.1 keep-alive and an artificial response delay
of 25 ms (`ORIGIN_DELAY_MS`, `tc netem`) — without it the local network is too
fast for the flaws in exercises 12–13 to give a measurable signal.
`GET /nginx_status` shows the number of connections and requests.

## Quick start

0. Create your own working branch: `git switch -c my-exercises` — the exercises
   modify the application files (`app/images.py`, `app/fetch.py`,
   `app/storage.py`, `app/reports.py`, `app/profiling.py`, `app/main.py`); the
   clean `english` branch is a free reset of the course, and `git diff english`
   will show you at the end everything you have built.
1. Environment (on macOS plain `python` often does not exist or points to the
   system 3.9 — give the version explicitly):
   `python3.14 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. Data corpus: `python scripts/gen_corpus.py` (it must exist BEFORE
   `docker compose up`, because the `origin` service mounts
   `data/origin_images` as a read-only volume).
3. Backend: `docker compose up -d --build --wait` → Pyroscope UI:
   `http://127.0.0.1:4040` (no login). The first time the images are built, and
   Pyroscope needs about 60–90 s after startup before `/ready` stops returning
   503 — `--wait` waits for the `healthy` state.
4. Variables: `cp .env.example .env` (the course has no secrets — only local
   addresses).
5. Start with `exercises/00-theory.md`, then `exercises/01.md`.

## Running the application

```bash
python scripts/reset_uploads.py      # clears data/uploads/ — do this before every measurement
uvicorn app.main:app --host 127.0.0.1 --port 8040
# in a second terminal:
python loadgen.py --duration 30 --concurrency 5 --scenario mixed
```

You choose the profiler mode (CPU or wall-clock) **at process startup**:
`PYROSCOPE_WALL=1 uvicorn app.main:app --host 127.0.0.1 --port 8040` (exercise
11). There is no way to change the mode in a running application — changing it
means a restart.
`curl -s 127.0.0.1:8040/health` returns, among other things, the `pid` (handy
for py-spy and memray) and the profiling state (`"mode": "cpu"|"wall"`). In the
uvicorn terminal you will also see the line `Profiling active (Pyroscope: …, mode: …)`.

`GET /debug/objects` (independent of `profiling.py`) returns counters of live objects: `live_pipelines`, `event_subscribers`, `publish_us` — for exercise 9.

As long as `app/profiling.py` still has a `TODO`, the `/debug/memory` endpoint
returns HTTP 501 with a hint about which exercise unlocks it — the rest of the
application (upload/thumbnails/filters/fetch/reports) works independently of
the profiling state.
You check the "done" criteria with a script: `python check.py exNN` (or
`python check.py --all`).

**Remember two things.** (1) After every code or mode change, restart the
application; `check.py` asks Pyroscope only for samples **since the start of
the current process**, so after a restart generate traffic and wait about 15–20
s for the samples to appear. (2) Data from previous runs stays in the Pyroscope
volume (`docker compose down -v` clears it); set the time windows in the UI to
the last few minutes.

Stuck? First the graduated hints in `solutions/hints/` (direction → API →
pseudocode), and only then the ready-made versions in `solutions/` (see
`solutions/README.md`).

## Repository map

| Path | What it is |
|---------|-------|
| `app/`       | the pixelforge application (`profiling.py` — the topic layer of the course; `images.py`/`fetch.py`/`reports.py`/`storage.py`/`main.py` — the domain, works from the start) |
| `data/`      | image corpus (`scripts/gen_corpus.py`) + runtime storage (`data/uploads/`, outside git) |
| `exercises/` | 16 exercises + `00-theory.md` + block readings (`04a`/`06a`/`09a`/`11a`) + `glossary.md` |
| `solutions/` | ready-made versions of modules, flaw-fix snippets, hints, answers |
| `scripts/`   | `gen_corpus.py` (corpus), `reset_uploads.py` (clearing uploads) |
| `check.py`   | machine verification of the "done" criteria per exercise |
| `loadgen.py` | load generator (`--concurrency`/`--duration`/`--scenario`/`--pool`/`--report-ids`/`--requests`; the `pipeline` scenario = the same request over and over) |
| `profiles/`  | a place for exercise artifacts (outside git) |
| `docker-compose.yml` | Pyroscope + the `origin` service (nginx; static images to download) |

## Tools used in the course

- **Grafana Pyroscope** (Docker, `:4040`) — continuous profiling, flame graphs,
  tagging, comparing profiles over time.
- **py-spy** — inspecting a live Python process from the outside (top/dump/record),
  without changing the code or restarting.
- **memray** — an allocator-level memory profiler, leak detection
  (`--leaks`).
- **cProfile + snakeviz** — a deterministic offline profile of a single
  function, visualized in the browser.
- **`tracemalloc`** (stdlib) — tracking Python allocations per line of code
  (off by default: it slows pure-Python loops down by about 11×; you enable it
  with `PIXELFORGE_TRACEMALLOC=1` or with the first `GET /debug/memory`).
- **`timeit`** (stdlib) — comparative microbenchmarks.

## Notes

- **Cost:** the course uses no LLM or paid service — $0.
- **Ports:** the application `127.0.0.1:8040` (locally), Pyroscope `127.0.0.1:4040`
  and `origin` `127.0.0.1:8041` (Docker; ports exposed on the loopback
  interface only). If they collide with another program, change them in
  `docker-compose.yml` and `.env` — do not run two heavy observability stacks
  at the same time. Container names depend on the compose project
  (`<project>-pyroscope-1`, `<project>-origin-1`); logs: `docker compose logs origin`.
- **py-spy and memray without `sudo`.** On macOS `py-spy` always requires `sudo`
  (macOS lets only root or a signed debugger read another process's memory;
  SIP is a separate block on protected system binaries that even root cannot
  bypass), and so does `memray attach`. Paths that need no administrator
  privileges:
  - **memray:** `memray run -o profiles/file.bin -m uvicorn app.main:app --host
    127.0.0.1 --port 8040` starts the application directly under memray's
    control (it requires no privileges); after stopping it (Ctrl+C) run
    `memray flamegraph --leaks -o profiles/file.html profiles/file.bin`
    (exercise 8).
  - **py-spy:** in a Linux container
    `docker run --rm -it --cap-add SYS_PTRACE python:3.14-slim …` (the `slim`
    image has neither `pgrep`, `ps` nor `curl` — take the PID from `$!`, for
    pixelforge from `/health`). With the default
    PID isolation the container does not see the host's processes, so py-spy
    can diagnose there only a program started in that same container. Without
    `sudo` you therefore do exercise 2 entirely in one container (application,
    loadgen, py-spy and `check.py ex02`; how to prepare it — repository,
    corpus, `docker exec` — is in exercise 2, "Theory in a nutshell");
    `solutions/gil_demo.py` (exercise 10) is only for practising the commands.
  On Linux outside a container, attaching by PID usually needs root; without
  it, only if the system's ptrace policy and your permissions allow it (e.g.
  `CAP_SYS_PTRACE` or `kernel.yama.ptrace_scope` = 0).
- **memray does NOT work on Windows** (it relies on mechanisms specific to
  Linux/macOS) — on Windows use WSL2.
- **`fsync` on macOS** does not flush the disk's hardware cache (`F_FULLFSYNC`
  does that) — the flaw from exercise 14 is less visible there than on Linux.
- **Do not commit profiling artifacts permanently** — the `profiles/` directory
  (generated `.prof`/`.html`/`.bin`/`.txt`/`.md` files from the exercises) is in
  `.gitignore`, as is `data/uploads/`.
