#!/usr/bin/env python3
"""check.py — machine verification of the "definition of done" criteria for the pyprof course.

Usage:
    python check.py ex01        # checks the criteria of exercise 1
    python check.py --all       # checks all the implemented exercises

Two kinds of assertions:
  - FILE-BASED / static (grep over app/*.py, existence of files in profiles/) —
    they always work and need neither a running application nor Docker.
  - NETWORK (HTTP to the application :8040 and/or Pyroscope :4040) — if the service
    does not respond within 2s, the result is SKIP (not FAIL) — a missing infrastructure
    is not the same thing as an exercise you have not passed.

Criteria that cannot be checked by a machine (e.g. "you understand why") stay only
in the exercise text, not here.
"""

from __future__ import annotations

import json
import pstats
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
APP_DIR = REPO_ROOT / "app"
PROFILES_DIR = REPO_ROOT / "profiles"

APP_BASE_URL = "http://127.0.0.1:8040"
PYROSCOPE_BASE_URL = "http://127.0.0.1:4040"
HTTP_TIMEOUT = 2.0


class Skip(Exception):
    """Raised when an assertion needs unavailable infrastructure (not a FAIL)."""


class Fail(Exception):
    """Raised when an assertion ran, but the criterion is not met."""


# --- helpers -----------------------------------------------------------------


def _read(path: Path) -> str:
    if not path.exists():
        raise Fail(f"Missing file: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def _read_artifact(name: str) -> str:
    """The content of an artifact from profiles/ — it must exist, not be empty and not be a template."""
    path = PROFILES_DIR / name
    _file_nonempty(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if "PLACEHOLDER" in text:
        raise Fail(f"profiles/{name} contains PLACEHOLDER — save your own result.")
    return text


def _file_nonempty(path: Path) -> None:
    if not path.exists():
        raise Fail(
            f"Missing file {path.relative_to(REPO_ROOT)} — generate it following "
            f"the steps of the exercise."
        )
    if path.stat().st_size == 0:
        raise Fail(f"File {path.relative_to(REPO_ROOT)} is empty.")


def _http_json(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            status = resp.status
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = exc.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise Skip(f"Unavailable: {url} ({exc})")
    try:
        parsed = json.loads(payload) if payload else {}
    except json.JSONDecodeError:
        parsed = {}
    return {"status": status, "body": parsed}


def _health() -> dict:
    """GET /health — 200 and JSON with the application state (pid, started_at, profiling)."""
    resp = _http_json("GET", f"{APP_BASE_URL}/health")
    if resp["status"] != 200:
        raise Fail(f"GET /health → HTTP {resp['status']}, expected 200")
    return resp["body"]


def _pyroscope_samples(selector: str, since: float) -> int:
    """The total value of the profile (`numTicks`) in Pyroscope since `since` (epoch, seconds).

    We ask about the window SINCE THE APPLICATION STARTED (at most the last hour),
    not about "the last hour" in general — Pyroscope remembers data from earlier
    runs (including from the solutions), and those must not count. The query
    filters by time window and labels, not by process or profiler mode: samples
    of another process of the same service sent in that window would count too.
    The value is in profile units (ns of aggregated sample weight), not a sample
    count; 0 = no data.
    """
    now = time.time()
    query = f"process_cpu:cpu:nanoseconds:cpu:nanoseconds{{{selector}}}"
    params = urllib.parse.urlencode(
        {
            "query": query,
            "from": int(max(since, now - 3600) * 1000),
            "until": int(now * 1000),
            "format": "json",
        }
    )
    url = f"{PYROSCOPE_BASE_URL}/pyroscope/render?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:  # before URLError: HTTPError is its subclass
        raise Fail(f"Pyroscope render → HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise Skip(f"Unavailable: {url} ({exc})")
    return int(body.get("flamebearer", {}).get("numTicks", 0))


# --- assertions per exercise -----------------------------------------------


def check_ex01() -> str:
    """Ex. 01: init_profiling — the application sends samples to Pyroscope."""
    health = _health()
    if not health.get("profiling", {}).get("configured"):
        raise Fail(
            "GET /health: profiling.configured = false — init_profiling() "
            "did not work (a TODO skeleton?). Implement it in "
            "app/profiling.py and restart the application."
        )
    ticks = _pyroscope_samples('service_name="pixelforge"', health["started_at"])
    if ticks == 0:
        raise Fail(
            "Pyroscope has no service_name='pixelforge' samples in the window since "
            "the application started (at most the last hour). Generate traffic "
            "(python loadgen.py --duration 20 --concurrency 3) and wait about "
            "15-20 s for the samples to arrive."
        )
    return (
        "/health: profiling.configured; Pyroscope has pixelforge samples in the window "
        "since the application started (at most the last hour) "
        f"({ticks / 1e9:.2f} s of aggregated sample weight)"
    )


def check_ex02() -> str:
    """Ex. 02: py-spy top/dump on a live process — a saved snapshot."""
    text = _read_artifact("ex02_dump.txt")
    if "Thread" not in text or "app/" not in text:
        raise Fail(
            "profiles/ex02_dump.txt does not look like the output of `py-spy dump --locals` "
            "from the pixelforge application (missing the word 'Thread' and/or the paths 'app/'). "
            "Take the dump while loadgen is still sending traffic — after it ends the "
            "threads wait outside app/ code."
        )
    return (
        "profiles/ex02_dump.txt: looks like a dump of thread stacks with app/ frames "
        "(content heuristic — compare 'Process <pid>' with /health yourself)"
    )


def check_ex03() -> str:
    """Ex. 03: cProfile + snakeviz — a saved .prof profile."""
    path = PROFILES_DIR / "ex03_sepia.prof"
    _file_nonempty(path)
    try:
        stats = pstats.Stats(str(path))
    except Exception as exc:  # noqa: BLE001
        raise Fail(f"profiles/ex03_sepia.prof is not a valid cProfile file: {exc!r}")
    if not any(func[2] == "_sepia_naive" for func in stats.stats):
        raise Fail("profiles/ex03_sepia.prof has no _sepia_naive function — you are profiling the wrong path.")
    return "profiles/ex03_sepia.prof: a valid cProfile, _sepia_naive is visible"


def check_ex04() -> str:
    """Ex. 04: tag_wrapper — per-endpoint tags visible in Pyroscope."""
    health = _health()
    ticks = _pyroscope_samples('service_name="pixelforge",endpoint=~".+"', health["started_at"])
    if ticks == 0:
        raise Fail(
            "Pyroscope has no pixelforge samples with the 'endpoint' tag in the window "
            "since the application started (at most the last hour) — check "
            "tag_wrapper() in app/profiling.py and generate traffic "
            "(python loadgen.py --duration 15) AFTER restarting the application."
        )
    return (
        "Pyroscope has pixelforge samples with the 'endpoint' tag in the window since "
        "the application started (at most the last hour) "
        f"({ticks / 1e9:.2f} s of aggregated sample weight)"
    )


def check_ex05() -> str:
    """Ex. 05: fixing the naive sepia — Image.convert(matrix=...) instead of a loop."""
    src = _read(APP_DIR / "images.py")
    # Note: we do NOT check for 'convert("RGB", matrix=' alone — that snippet
    # also appears in the _sepia_naive docstring as a description of the fix (a false PASS
    # on unchanged code). We look specifically for a use of SEPIA_MATRIX in the code.
    if "matrix=SEPIA_MATRIX" not in src:
        raise Fail(
            "app/images.py still computes sepia with a naive Python loop — replace "
            "the call _sepia_naive(img) with img.convert(\"RGB\", "
            "matrix=SEPIA_MATRIX) (see solutions/filters_snippets.py)."
        )
    return "app/images.py: the sepia filter computed by Image.convert(matrix=...)"


def check_ex06() -> str:
    """Ex. 06: timeit microbenchmarks — saved results."""
    text = _read_artifact("ex06_timeit.txt")
    if len(re.findall(r"loops?, best of", text)) < 2:
        raise Fail("profiles/ex06_timeit.txt: expected two `python -m timeit` results (naive and Pillow).")
    return "profiles/ex06_timeit.txt: two timeit results (naive vs Pillow)"


def check_ex07() -> str:
    """Ex. 07: tracemalloc via /debug/memory (two calls, the second must have data)."""
    first = _http_json("GET", f"{APP_BASE_URL}/debug/memory")
    if first["status"] == 501:
        raise Fail("GET /debug/memory → 501: profiling.py is not implemented yet")
    if first["status"] != 200:
        raise Fail(f"GET /debug/memory → HTTP {first['status']}, expected 200")
    resp = _http_json("GET", f"{APP_BASE_URL}/debug/memory")
    top = resp["body"].get("top_allocations", [])
    if not top:
        raise Fail(
            "GET /debug/memory returned an empty top_allocations list — "
            "tracemalloc is not running (start_memory_tracking() should be called in lifespan)."
        )
    if not {"file", "line", "size_kb", "count"} <= set(top[0]):
        raise Fail(f"A top_allocations entry has the wrong fields: {top[0]}")
    return f"GET /debug/memory → 200, {len(top)} top_allocations entries"


def check_ex08() -> str:
    """Ex. 08: fixing the THUMBNAIL_CACHE leak (F1) + memray --leaks."""
    html = _read_artifact("ex08_leak.html")
    if "images.py" not in html:
        raise Fail("profiles/ex08_leak.html does not contain 'images.py' — it is not a memray report from pixelforge.")
    src = _read(APP_DIR / "images.py")
    # Note: we do NOT check for bare keywords like "TTL"/"lru_cache" — they
    # also appear in the THUMBNAIL_CACHE docstring as a DESCRIPTION of a possible fix
    # (a false PASS on unchanged code). We look for specific functions
    # that actually implement eviction (see solutions/images_snippets.py).
    if "_cache_get" not in src or "_cache_put" not in src:
        raise Fail(
            "app/images.py: I can see no _cache_get/_cache_put functions or any other "
            "concrete eviction implementation — THUMBNAIL_CACHE still grows "
            "without bound (see solutions/images_snippets.py)."
        )
    return "profiles/ex08_leak.html saved; app/images.py has cache eviction logic"


def _live_pipeline_growth(requests: int = 30) -> tuple[int, int]:
    """Runs `requests` identical pipeline requests (F1b) INSIDE the check.py process and
    returns (live FilterPipeline objects, EVENTS bus subscribers minus the initial state).

    The test is behavioral (it counts live objects through gc), so it cannot be
    fooled by a comment or docstring in the code, and it does not need a running application.
    """
    import gc
    import importlib

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        images = importlib.import_module("app.images")
        pipeline = importlib.import_module("app.pipeline")
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        raise Fail(f"Cannot import app.images / app.pipeline: {exc!r}")
    config = importlib.import_module("app.config")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    probe = config.UPLOAD_DIR / "ex09check.jpg"
    Image.new("RGB", (200, 150), (90, 120, 200)).save(probe, format="JPEG")
    try:
        before = len(pipeline.EVENTS)
        for _ in range(requests):
            images.apply_pipeline("ex09check", "sketch")
        gc.collect()
        live = sum(1 for o in gc.get_objects() if type(o) is pipeline.FilterPipeline)
        return live, len(pipeline.EVENTS) - before
    except Exception as exc:  # noqa: BLE001
        raise Fail(f"images.apply_pipeline('ex09check', 'sketch') raised an exception: {exc!r}")
    finally:
        probe.unlink(missing_ok=True)


def check_ex09() -> str:
    """Ex. 09: fixing the F1b leak (a graph per request registered in EVENTS) + diagnosis notes."""
    requests = 30
    live, subscribers = _live_pipeline_growth(requests)
    # A constant, not a function of the number of requests: a shared graph = 1 (per preset), unsubscribe in finally = 0.
    if live > 2 or subscribers > 2:
        raise Fail(
            f"After {requests} identical requests, {live} FilterPipeline objects are alive and the EVENTS bus "
            f"grew by {subscribers} subscribers — the graph is still leaking (the count grows with the number of requests). "
            f"Fix it in app/images.py (see solutions/pipeline_snippets.py)."
        )
    html = _read_artifact("ex09_leak.html")
    if "pipeline.py" not in html:
        raise Fail(
            "profiles/ex09_leak.html does not contain 'pipeline.py' — it is not a memray --leaks report "
            "from /pipeline traffic (the state BEFORE the fix, kept as evidence of the diagnosis)."
        )
    src = _read(APP_DIR / "reports.py")
    if re.search(r'report\s*\+=\s*f"', src):
        raise Fail("app/reports.py has 'report +=' concatenation in a loop — restore the list + join (★ F7).")
    notes = _read_artifact("ex09_notes.md")
    missing = [w for w in ("get_referrers", "EVENTS") if w not in notes]
    if len(notes) < 200 or missing:
        raise Fail(
            "profiles/ex09_notes.md: write down the numbers (RSS/instance count before and after), the reference chain from "
            "gc.get_referrers to EVENTS and the justification of the fix you chose (min. 200 characters; the words "
            f"`get_referrers` and `EVENTS`){'; missing: ' + ', '.join(missing) if missing else ''}."
        )
    return (
        f"after {requests} identical requests: {live} live FilterPipeline objects, bus +{subscribers}; "
        "ex09_leak.html and ex09_notes.md saved"
    )


def check_ex10() -> str:
    """Ex. 10: the GIL — comparing threads vs processes (gil_demo.py)."""
    text = _read_artifact("ex10_gil_notes.txt")
    numbers = re.findall(r"\d+[.,]\d+", text)
    if len(numbers) < 3 or not all(w in text.lower() for w in ("sequential", "threads", "processes")):
        raise Fail(
            "profiles/ex10_gil_notes.txt: expected three times (sequential, "
            "threads, processes) with a decimal part, e.g. 'sequential 0.65 s'."
        )
    return f"profiles/ex10_gil_notes.txt: {len(numbers)} numbers, three modes described"


def check_ex11() -> str:
    """Ex. 11: wall-clock mode chosen at startup — samples with the mode=wall tag."""
    health = _health()
    prof = health.get("profiling", {})
    if not prof.get("configured"):
        raise Fail("GET /health: profiling.configured = false — do exercise 01 first.")
    if not prof.get("wall"):
        raise Fail(
            "The application runs in CPU mode (profiling.wall = false). Start it "
            "again with PYROSCOPE_WALL=1 (the mode is chosen at process start) "
            "and make sure init_profiling() handles the `wall` parameter."
        )
    ticks = _pyroscope_samples('service_name="pixelforge",mode="wall"', health["started_at"])
    if ticks == 0:
        raise Fail(
            "No samples with the mode=wall tag since the process start — init_profiling() "
            "should add the mode=wall tag and oncpu=False, gil_only=False. "
            "Generate traffic and wait about 15-20 s."
        )
    return f"/health: wall mode; Pyroscope has mode=wall samples since the process start ({ticks / 1e9:.1f} s)"


def check_ex12() -> str:
    """Ex. 12: fixing F3a — a shared httpx.AsyncClient."""
    fetch_src = _read(APP_DIR / "fetch.py")
    main_src = _read(APP_DIR / "main.py")
    if "async with httpx.AsyncClient() as client:" in fetch_src:
        raise Fail(
            "app/fetch.py still creates a new httpx.AsyncClient() per call "
            "— move the client to app.state (see solutions/fetch_snippets.py)."
        )
    if "http_client" not in main_src:
        raise Fail(
            "app/main.py: I can see no shared client in app.state "
            "(expected e.g. app.state.http_client in lifespan)."
        )
    return "No per-request httpx.AsyncClient(); a shared client in app.state"


def check_ex13() -> str:
    """Ex. 13: fixing F3b — fetch_batch in parallel through asyncio.gather."""
    src = _read(APP_DIR / "fetch.py")
    # Note: it is NOT enough to search for the substring "asyncio.gather" — it also appears
    # in the docstring as a description of the fix (a false PASS on unchanged code).
    # We look for a REAL call (await ... asyncio.gather().
    if not re.search(r"await\s+asyncio\.gather\(", src):
        raise Fail(
            "app/fetch.py: fetch_batch still downloads the URLs sequentially in a "
            "for loop — replace it with `await asyncio.gather(...)` (see "
            "solutions/fetch_snippets.py)."
        )
    return "app/fetch.py: fetch_batch uses asyncio.gather"


def check_ex14() -> str:
    """Ex. 14: fixing F4 — a buffer + one write/fsync instead of fsync per chunk."""
    src = _read(APP_DIR / "storage.py")
    if "for offset in range(0, len(data), chunk_size):" in src:
        raise Fail(
            "app/storage.py: save_bytes still splits the write into chunks with "
            "flush()+fsync() after each one — replace it with a single f.write(data) + one "
            "fsync (see solutions/storage_snippets.py)."
        )
    return "app/storage.py: save_bytes writes with a single write() (no fsync per chunk)"


def check_ex15() -> str:
    """Ex. 15: comparing profiles over time (the version tag) — notes saved."""
    text = _read_artifact("ex15_comparison.md")
    if "version" not in text or len(text) < 200:
        raise Fail("profiles/ex15_comparison.md: describe the comparison of the `version` tag (min. 200 characters, mention `version`).")
    return "profiles/ex15_comparison.md: a description of the version comparison"


def check_ex16() -> str:
    """Ex. 16: the final challenge — your own diagnosis BEFORE checking the key."""
    text = _read_artifact("ex16_diagnosis.md")
    if text.count("→") < 4:
        raise Fail("profiles/ex16_diagnosis.md: for each of the 4 symptoms write \"symptom → evidence → hypothesis\" (min. 4 arrows →).")
    if not (REPO_ROOT / "solutions" / "ex16_answers.md").exists():
        raise Fail("Missing solutions/ex16_answers.md (a course error, please report it).")
    return "profiles/ex16_diagnosis.md saved (your diagnosis)"


CHECKS = {
    "ex01": check_ex01,
    "ex02": check_ex02,
    "ex03": check_ex03,
    "ex04": check_ex04,
    "ex05": check_ex05,
    "ex06": check_ex06,
    "ex07": check_ex07,
    "ex08": check_ex08,
    "ex09": check_ex09,
    "ex10": check_ex10,
    "ex11": check_ex11,
    "ex12": check_ex12,
    "ex13": check_ex13,
    "ex14": check_ex14,
    "ex15": check_ex15,
    "ex16": check_ex16,
}


def run_one(name: str) -> str:
    fn = CHECKS.get(name)
    if fn is None:
        print(f"Unknown exercise: {name}. Available: {', '.join(sorted(CHECKS))}")
        return "UNKNOWN"
    try:
        detail = fn()
        print(f"[PASS] {name}: {detail}")
        return "PASS"
    except Skip as exc:
        print(f"[SKIP] {name}: {exc}")
        return "SKIP"
    except Fail as exc:
        print(f"[FAIL] {name}: {exc}")
        return "FAIL"
    except Exception as exc:  # noqa: BLE001 — an unexpected error must be visible too
        print(f"[FAIL] {name}: unexpected error: {exc!r}")
        return "FAIL"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    arg = sys.argv[1]
    if arg == "--all":
        results = {name: run_one(name) for name in CHECKS}
        print()
        print("=== Summary ===")
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for name, result in results.items():
            counts[result] = counts.get(result, 0) + 1
        for name, result in results.items():
            print(f"  {name}: {result}")
        print(
            f"Total: {counts.get('PASS', 0)} PASS, {counts.get('FAIL', 0)} FAIL, "
            f"{counts.get('SKIP', 0)} SKIP (out of {len(results)} exercises)"
        )
        if counts.get("FAIL", 0) > 0:
            raise SystemExit(1)
    else:
        result = run_one(arg)
        if result in ("FAIL", "UNKNOWN"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
