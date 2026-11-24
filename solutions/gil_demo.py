"""solutions/gil_demo.py — a GIL contention demo (exercise 10, F5).

This script is NOT part of the pixelforge service — it is a standalone program, run
by hand, demonstrating why threads (threading) do NOT speed up
CPU-bound computation in CPython (the GIL lets only one thread at a time
execute Python bytecode), while processes (multiprocessing) do, because each
process has its OWN interpreter and its OWN GIL.

The CPU-bound task: counting primes in a given range (pure
Python, no C library releasing the GIL) — analogous to flaw F2
(naive sepia) in app/images.py, only isolated into a single file so that it
can be run in many threads/processes at once and timed.

The total work is CONSTANT (primes in the interval [0, TOTAL)); the modes differ
only in how it is divided up. The interval is cut into chunks of CHUNK numbers, handed to the workers
in turn (round-robin), so each has a similar amount of work, and the sum of results is identical in every mode.

Usage:
    python solutions/gil_demo.py sequential        # baseline: 1 thread, all the work
    python solutions/gil_demo.py threads 4         # 4 threads (expected: NO speedup)
    python solutions/gil_demo.py processes 4       # 4 processes (expected: a speedup)

The script runs for a few to a dozen or so seconds in sequential/threads mode — long enough to
attach py-spy from a second terminal (macOS requires sudo; Linux: --cap-add SYS_PTRACE):
    sudo py-spy dump --pid $(pgrep -f gil_demo | head -1) --locals
    sudo py-spy top --gil --pid $(pgrep -f gil_demo | head -1)
    py-spy record --gil --threads -d 5 -o profiles/ex10_gil.svg --pid <PID>
NOTE: the --gil option is an argument of the SUBCOMMAND (`py-spy top --gil`), not of py-spy
(`py-spy --gil top` returns an error).
`py-spy top --gil` shows that at any given moment ONLY ONE thread holds the GIL.
In `processes` mode every process has a separate PID and its own GIL.

Free-threaded Python (3.14t, `sys._is_gil_enabled() == False`) has NO GIL — there
threads do speed things up. The results of the exercise apply to a regular build with the GIL; the script
prints which build you ran.
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

TOTAL = 5_000_000  # the upper bound of the interval of numbers checked IN FULL (constant work)
DEFAULT_WORKERS = 4


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


CHUNK = 50_000  # chunks assigned to the workers in turn (round-robin) — evens out the cost


def count_primes(offset: int, step: int) -> int:
    """Counts primes in chunks number offset, offset+step, ... of the interval [0, TOTAL).

    CPU-bound, pure Python (does not release the GIL). Chunks instead of remainders of a division,
    because even numbers are trivial and the "even" worker would have almost no work."""
    total = 0
    for k in range(offset, TOTAL // CHUNK, step):
        total += sum(1 for n in range(k * CHUNK, (k + 1) * CHUNK) if is_prime(n))
    return total


def run_sequential(n_workers: int) -> int:
    return count_primes(0, 1)  # all the work in one thread (n_workers is ignored)


def run_threads(n_workers: int) -> int:
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        results = pool.map(lambda i: count_primes(i, n_workers), range(n_workers))
    return sum(results)


def run_processes(n_workers: int) -> int:
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        results = pool.map(_count_primes_star, [(i, n_workers) for i in range(n_workers)])
    return sum(results)


def _count_primes_star(args: tuple[int, int]) -> int:
    # A module-level function (not a lambda) — multiprocessing has to pickle it
    # (on macOS the default start method is "spawn").
    return count_primes(*args)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "sequential"
    n_workers = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_WORKERS

    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"gil_demo: mode={mode} workers={n_workers} total={TOTAL} GIL={'enabled' if gil_enabled else 'DISABLED (free-threaded)'}")
    print(f"PID: {__import__('os').getpid()} — use this PID in py-spy")

    start = time.perf_counter()
    if mode == "sequential":
        total = run_sequential(n_workers)
    elif mode == "threads":
        total = run_threads(n_workers)
    elif mode == "processes":
        total = run_processes(n_workers)
    else:
        raise SystemExit(f"Unknown mode: {mode!r}. Use: sequential | threads | processes")
    elapsed = time.perf_counter() - start

    print(f"Primes found (total): {total}")
    print(f"Time: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
