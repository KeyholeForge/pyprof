# Index of exercises and readings

The order is progressive — each exercise builds on the previous one. The
theoretical readings (no tasks) precede the blocks they concern. Start with
`exercises/00-theory.md` — the concept map of the whole course.

The times in the table are the approximate working time **without** waiting for
Pyroscope to start (about 90 s on the first `docker compose up`) and for samples
to appear after traffic (about 15–20 s). The whole course: about 10–11 hours.

## Skills map

After finishing the course you can:
- run continuous profiling and read a flame graph, filter by tags (ex. 1, 4)
- inspect a live process without a restart (py-spy top/dump) (ex. 2)
- profile a single function offline and compare implementations with a microbenchmark (ex. 3, 6)
- diagnose and fix a CPU-bound flaw (a Python loop → a native operation) (ex. 5)
- find a growing cache through RSS, tracemalloc and memray, fix it with eviction (ex. 7-8)
- tell a true leak from a cache with the "same request × N" test, **find who holds the reference** (`gc.get_referrers`) and fix a registry leak in two ways: a shared graph vs unsubscribing (ex. 9); check by measurement whether a micro-optimization matters (★ Bonus B in ex. 9)
- explain and demonstrate the GIL — why threads do not speed up CPU-bound code; **decide "are we computing or waiting"** from wall-clock time and CPU time (ex. 10)
- choose the profiler mode (cpu / wall) at startup and diagnose a frozen event loop; recognize three kinds of loop blocking (`sleep`, CPU, `fsync`) and the **limits of a sampling profiler** — a suspended coroutine is invisible, tags in `async def` get mixed up (ex. 11, reading 11a)
- diagnose network flaws (a new client per request, sequential fan-out) through the **connection count, the time and the `trace` hook**, not through a wide frame in the profile (ex. 12-13)
- diagnose a disk flaw (excess fsync): visible in wall, almost invisible in cpu; know how macOS differs from Linux (ex. 14)
- compare the profiles of two versions of the application by the `version` tag and detect a performance regression (ex. 15)
- diagnose an incident with several flaws at once ONLY through tools, choosing the tool for the kind of waiting and separating overlapping symptoms (ex. 16)

<!-- This map WAS WRITTEN BEFORE the list of exercises and determined their number
     (METODYKA §5). Every exercise builds at least one skill from the map. Full
     description: solutions/todo.md -->

## Exercises

| #   | File                                  | Time    | What you do |
|-----|----------------------------------------|---------|-----------|
| —   | `exercises/00-theory.md`              | ~30 min | **Reading:** the concept map of profiling (read it first) |
| 1   | `exercises/01.md`                     | ~30 min | Stack setup + `init_profiling` + the first flame graph in Pyroscope |
| 2   | `exercises/02.md`                     | ~20 min | py-spy top/dump on a live process, without a restart |
| 3   | `exercises/03.md`                     | ~25 min | cProfile + snakeviz — an offline profile of one function |
| 4   | `exercises/04.md`                     | ~35 min | per-endpoint `tag_wrapper` + reading flame graphs + mini-incident (end of block A) |
| —   | `exercises/04a-cpu-internals.md`      | ~15 min | **Reading:** the cost of operations in Python, interpreter overhead (before block B) |
| 5   | `exercises/05.md`                     | ~30 min | Diagnosing and fixing a naive CPU filter (F2) |
| 6   | `exercises/06.md`                     | ~25 min | Microbenchmarks (`timeit`) + CPU mini-incident (end of block B) |
| —   | `exercises/06a-cpython-memory.md`     | ~15 min | **Reading:** CPython memory internals; cache / leak / backlog (before block C) |
| 7   | `exercises/07.md`                     | ~25 min | `tracemalloc` via `/debug/memory` (×11 overhead) |
| 8   | `exercises/08.md`                     | ~40 min | RSS, tracemalloc and memray — diagnosing and fixing an unbounded thumbnail cache (F1) |
| 9   | `exercises/09.md`                     | ~60 min | A true memory leak (F1b): a graph per request in a global event bus — the "same request × N" test, tracemalloc/memray, `gc.get_referrers`, two fixes + a cache-or-leak mini-incident (end of block C); ★ F7 |
| —   | `exercises/09a-concurrency-gil-asyncio.md` | ~15 min | **Reading:** the GIL, threads, asyncio; "are we computing or waiting?" (before block D) |
| 10  | `exercises/10.md`                     | ~30 min | The GIL — why threads do not speed up CPU-bound code (`gil_demo.py`) |
| 11  | `exercises/11.md`                     | ~45 min | Wall mode at startup, a frozen loop (F6): `sleep`, CPU, `fsync`; the limits of the profiler + mini-incident (end of block D) |
| —   | `exercises/11a-io-network-disk.md`    | ~20 min | **Reading:** network and disk I/O + the limits of a sampling profiler (before block E) |
| 12  | `exercises/12.md`                     | ~30 min | TCP — a new httpx client per request (F3a): connection count → a shared client |
| 13  | `exercises/13.md`                     | ~30 min | Fan-out (F3b): time and the `trace` hook → `asyncio.gather`; when parallelism does not help |
| 14  | `exercises/14.md`                     | ~35 min | Disk — fsync after every chunk (F4), loop blocking, `F_FULLFSYNC` + I/O mini-incident (end of block E) |
| 15  | `exercises/15.md`                     | ~35 min | Comparing profiles by the `version` tag — a performance regression (F8) |
| 16  | `exercises/16.md`                     | ~75 min | The final challenge — 4 flaws at once (two phases), diagnosis ONLY through tools |

Concepts in a nutshell: `exercises/glossary.md`. Solutions and hints: the `solutions/` directory.
"Done" verification: `python check.py exNN` (or `python check.py --all`).

## Topic blocks

- **A — Foundations** (ex. 1-4): setup, tools (Pyroscope/py-spy/cProfile),
  tagging, reading flame graphs.
- **B — CPU** (ex. 5-6): diagnosing and fixing a computational flaw, microbenchmarks.
- **C — Memory** (ex. 7-9): tracemalloc, memray, an unbounded cache (F1), a true
  leak and "who holds it" (F1b).
- **D — Concurrency** (ex. 10-11): the GIL, threads vs processes, "are we computing or
  waiting?", cpu/wall modes, the event loop and its blocking, the limits of the profiler.
- **E — Network/disk** (ex. 12-14): the TCP connection count, fan-out, disk I/O — and
  choosing the tool: a profile or a stopwatch.
- **F — Final** (ex. 15-16): comparing profiles by the `version` tag, the final
  challenge (diagnosis without reading the code, overlapping symptoms).
