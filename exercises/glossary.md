# Glossary — pyprof

An alphabetical glossary of the terms used in `00-theory.md` and the block
readings (`04a`, `06a`, `09a`, `11a`). Each entry: a short definition + a
pointer to the exercise in which it materializes in practice. The full
explanations (definition → intuition → why it matters → common mistake) are in
the theory documents — here only a quick cheat sheet.

Exercise map: ex. 1 = setup/Pyroscope, ex. 2 = py-spy, ex. 3 = cProfile/snakeviz,
ex. 4 = flame graphs/tags, ex. 5-6 = CPU, ex. 7-9 = memory, ex. 10-11 = GIL/asyncio,
ex. 12-14 = network/disk, ex. 15 = diff/regression, ex. 16 = final.

---

**Are we computing or waiting** — the first diagnostic question: compare wall-clock
time with CPU time (`real` vs `user`). Equal → CPU-bound (processes, algorithm,
native code); `real` ≫ `user` → waiting (threads, `asyncio`, fewer connections). →
ex. 10-11.

**Arenas (pymalloc)** — large blocks of memory (1 MB by default) requested by the
CPython allocator from the operating system, divided into pools and blocks for
small objects. An arena goes back to the OS only when the WHOLE of it is empty —
which is why RSS does not always drop even though objects were freed. → ex. 7-9.

**Bound method** — the object `obj.method`: it holds a reference to
`obj` (`__self__`). Put into a global list of subscribers, it keeps `obj`
alive until someone removes it from there; `weakref.WeakMethod` is its
weak counterpart. → ex. 9.

**Bytecode** — a sequence of low-level instructions that CPython compiles Python
source code into before execution; it is executed by the interpreter loop, not
directly by the processor. → ex. 5-6.

**Connection pooling** — managing a pool of open, ready-to-reuse network
connections on the client side, so that subsequent requests do not have to
establish a new connection from scratch. → ex. 12-13.

**Continuous profiling** — continuous, cheap sampling of a running application
(here: Pyroscope) with the ability to compare profiles over time, as opposed to
one-off ad-hoc profiling. → ex. 1, 4, 15.

**cProfile** — Python's built-in tracing profiler; it records supported call
events (calls and returns of Python functions and of selected built-ins such as
`min`), so the call counts are exact for what it records, but its overhead is
usually higher than sampling and can distort the timings;
the result can be viewed with, among others, `snakeviz`. → ex. 3.

**Event loop** — the loop in `asyncio`, usually running in a single
thread, which manages the execution of many coroutines; it switches between them
at `await` points. → ex. 10-11.

**Fan-out** — one request initiating many independent I/O operations;
sequential fan-out adds up the times, parallel fan-out (`asyncio.gather`) limits the
time to that of the slowest operation. → ex. 12-13.

**Flame graph** — a visualization of a call-stack profile: the Y axis = stack depth,
the X axis = aggregation of samples (NOT time), frame width = self/total time. →
ex. 2, 4.

**fsync** — a system call (`os.fsync`) that forces the physical write of
data from the file system buffer to the storage medium, blocking until it completes; expensive
when called often. → ex. 14.

**GC (generational garbage collector)** — the CPython mechanism that detects
reference CYCLES (which refcounting alone will not remove); it divides objects into 3
generations (0 the youngest, checked most often). It does not remove objects still
reachable through live references (e.g. entries in an unbounded cache or a graph
registered in a global event bus). → ex. 7-9.

**gc.get_referrers(obj)** — a function that returns the objects that directly
hold `obj`; repeated upward it gives a "who holds it" chain all the way to a module-level
global variable. It answers the question that neither tracemalloc nor
memray answers (they say who allocated). → ex. 9.

**GIL (global interpreter lock)** — a lock that allows only one
thread at a time to execute Python bytecode in a given process; it exists mainly
to simplify the safety of refcounting. It makes `threading` not
speed up CPU-bound code. → ex. 10-11.

**gil_only (Pyroscope)** — a client parameter: True = sample only the threads holding the
GIL (skips sleeping and waiting ones), False = the waiting threads as well. In wall mode it must
be False, otherwise `sleep` or `fsync` disappear from the profile. → ex. 1, 11.

**idle (idle samples)** — samples of threads that are doing nothing (e.g. waiting for a
task in a pool: `Condition.wait`). In wall mode they can make up most of
the profile of the whole service; filter by `endpoint`. → ex. 11.

**Interpreter loop** — the main CPython loop (`ceval.c`) that fetches,
decodes and executes successive bytecode instructions; the source of the
per-instruction overhead in pure Python code. → ex. 5-6.

**Keep-alive** — an HTTP mechanism that keeps the TCP connection open and
reused for subsequent requests to the same host, instead of closing it after
a single request. → ex. 12-13.

**memray** — a tool for profiling Python memory (offline `memray run`
or attaching to a live process with `memray attach <PID>` — PID positionally, ending the
tracking with `--duration N` or `memray detach <PID>`; on macOS `sudo`);
the report `memray flamegraph --leaks` shows only unfreed (live) allocations. →
ex. 7-9.

**Off-CPU / wall-clock (profile)** — a profile that counts all elapsed time,
including waiting for I/O (network, disk, `sleep`) — as opposed to
on-CPU. In this course: `oncpu=False, gil_only=False`, chosen ONCE at startup of the
process (`PYROSCOPE_WALL=1`, tag `mode=wall`); it cannot be switched in a running
process. It does not see a coroutine suspended on `await`. → ex. 11-14.

**On-CPU (profile)** — a profile that counts only the time in which a thread actually
executes instructions on the processor; it does NOT show time spent waiting for I/O. →
ex. 5-6, the default Pyroscope mode in this course (`oncpu=True, gil_only=True`, tag `mode=cpu`).

**Pickle / serialization (in the context of ProcessPoolExecutor)** — converting
function arguments and results into a form that can be sent between processes;
the IPC cost of `ProcessPoolExecutor`. → ex. 10.

**Plateau (RSS)** — the level at which a process's memory stops growing despite
continued traffic (e.g. a cache with a limit); unlike "a return to the starting value",
which the allocator usually does not give. → ex. 8.

**Pools and blocks (pymalloc)** — the division of a pymalloc arena: a pool (16 KiB in 64-bit CPython 3.13; 4 KiB in older or 32-bit builds) is divided
into blocks of a fixed size for a given size class of small objects. →
ex. 7-9.

**ProcessPoolExecutor** — a class from `concurrent.futures` that runs tasks
in separate processes (each with its own GIL), truly in parallel on many
cores; the cost: serialization of data and no shared memory. A workaround for
CPU-bound code given the limits of `threading`. → ex. 10.

**py-spy** — an external sampling profiler (it needs no changes to the
application code); `py-spy top`, `py-spy dump --locals`, `py-spy record -o out.svg`,
`py-spy top --gil` (only the threads holding the GIL; `--gil` is an option of the
subcommand, `py-spy --gil top` is a syntax error). Attaching to a running
process needs privileges: on macOS always sudo, on Linux usually sudo (or
`CAP_SYS_PTRACE`); in a Linux container started with `--cap-add SYS_PTRACE` it
works without sudo on processes of the same container. → ex. 2, 10.

**pymalloc** — CPython's own memory allocator optimized for small
objects (≤512 B); it requests large blocks (arenas) from the system and divides them into
pools/blocks, instead of calling `malloc` on every object allocation. → ex. 7-9.

**Pyroscope** — a continuous profiling backend (Grafana Pyroscope, in Docker
in this course); the `pyroscope-io` client is configured with
`pyroscope.configure(...)`, and blocks of code are tagged with `pyroscope.tag_wrapper(tags)`.
→ ex. 1, 4, 11, 15.

**Refcounting** — the reference counter (`ob_refcnt`) of every Python object;
when it drops to zero, the object is freed IMMEDIATELY, deterministically, without
the GC. It does not detect reference cycles. → ex. 7-9.

**RSS (resident set size)** — the real physical memory currently occupied
by a process in RAM; it does not drop immediately after Python objects are freed because
of the fragmentation of pymalloc arenas and the behavior of the system allocator. →
ex. 7-9.

**Sampling profiler** — a profiler that periodically takes "snapshots" of the call stack
(e.g. every 10 ms) instead of recording every call; low overhead, a statistical
result (py-spy, Pyroscope). An external sampler such as py-spy needs no code
change but by default briefly pauses the process for each sample. The
opposite: a tracing profiler. →
ex. 1-2, 4.

**Self time / total time** — self time: the time/samples spent directly in
the code of a given function, without the functions it calls. Total time: self time +
the total time of all functions it calls. Key to
telling "where the problem sits" from "what is expensive as a whole" on a
flame graph. → ex. 2, 4-6.

**Semaphore (asyncio)** — a mechanism that limits the number of simultaneously
running operations (e.g. parallel HTTP requests) in `asyncio.gather`, so as not to
overload the target server or your own resources. → ex. 12-13.

**snakeviz** — a tool for visualizing `cProfile` results in the browser
(an interactive icicle/sunburst chart). → ex. 3.

**sys.getsizeof** — a function that returns the size of the object ITSELF (header +
direct data), without recursively counting the contents of containers (e.g. without the
elements of a list/dictionary). → ex. 7-9.

**tracemalloc** — a built-in Python module for tracking memory allocations with
attribution to a place in the code (file+line); `tracemalloc.start()`,
`tracemalloc.take_snapshot().statistics("lineno")`. → ex. 7.

**Tracing profiler** — a profiler that records supported events (such as
function calls and returns) as they occur, rather than sampling the stack
periodically (e.g. `cProfile`); exact call counts for what it records, but with
an overhead that grows with the
number of calls — it can distort the timings and even the proportions of fine-grained
code. The opposite:
sampling profiler. → ex. 3.

---

Related documents: `00-theory.md` (the theory), `04a-cpu-internals.md`,
`06a-cpython-memory.md`, `09a-concurrency-gil-asyncio.md`,
`11a-io-network-disk.md`.
