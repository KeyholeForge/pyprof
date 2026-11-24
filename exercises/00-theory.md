# 00. Theory: Python internals and profiling

A big primer, not an exercise — no tasks and no definition of done. The goal is
to build a map of concepts before you start exercises 1–16. Every concept
follows the same pattern:

> **Definition** → **Intuition/analogy** → **Why it matters** → **Common mistake**

Come back here whenever things stop adding up. Short definitions of all terms
are in `glossary.md`. Before the topic blocks you will find narrower readings:
`04a-cpu-internals.md`, `06a-cpython-memory.md`, `09a-concurrency-gil-asyncio.md`,
`11a-io-network-disk.md` — this document gives you the common foundation under
all four.

Context: throughout the course you profile a single application — **pixelforge**,
a FastAPI image-processing service (upload, thumbnails, filters, fetching from a
URL, batch reports). It has performance flaws built in on purpose; the
exercises ask you to find them with a profiler and then fix them. The examples
in this document refer to real modules of that application (`app/images.py`,
`app/fetch.py`, `app/storage.py`, `app/reports.py`), so you can see right away
where the theory meets the code you will be running.

---

## Bytecode and the CPython interpreter loop

**Definition.** CPython (the Python implementation you use) does not execute
`.py` files directly. It first compiles the source code to **bytecode** — a
sequence of simple low-level instructions (e.g. `LOAD_FAST`, `CALL`,
`BINARY_OP`; exact names change between versions — for a simple local read
CPython 3.14 often shows `LOAD_FAST_BORROW` where 3.11–3.13 show `LOAD_FAST`)
stored in `code` objects.
Bytecode from imported modules can be cached in `.pyc` files in
`__pycache__`. The heart of CPython is the **interpreter loop** in `ceval.c`,
which, in simplified terms, keeps doing the same thing:
fetch the next bytecode instruction, decode it, perform the corresponding
operation in C, and go back for the next one. Since 3.11 the loop also
specializes hot instructions for the types it sees (the adaptive interpreter),
which lowers but does not remove the per-instruction overhead.

**Intuition.** Think of a simultaneous interpreter who does not know the whole
speech in advance — they receive it sentence by sentence (instruction by
instruction) and translate on the fly into the "language of the machine" (C
function calls). Every translated sentence costs some overhead of the
translation itself — which is why Python is slower per operation than a
language compiled directly to machine code.

**Why it matters.** Understanding that Python runs by interpreting bytecode
explains two things that are key for profiling: (1) a profiler sees **Python
function call stack frames**, not individual CPU instructions — a flame graph
shows "you are in the function `_sepia_naive`, which calls `Image.load`", not
"you are in a `MOV` instruction". (2) Dispatch adds per-instruction overhead,
and the cost varies by operation — which is why a pure-Python `for` loop
doing millions of simple operations is usually much slower than equivalent
work implemented in a library written in C (such as Pillow or numpy), which
does all the work in ONE call from Python and runs the million-iteration loop
outside the interpreter. This is exactly the mechanism behind flaw F2 in
`app/images.py::_sepia_naive` — a double `for y / for x` loop over pixels in
Python instead of handing the per-pixel work to Pillow's C code. More on this
in `04a-cpu-internals.md`.

**Common mistake.** "A flame graph shows which LINE of C/machine code is slow,
so I can optimize at the CPU level." No — the standard Python profilers used
here (py-spy, cProfile, Pyroscope, in their default configuration in this
course) work at the level of **Python function frames**, not
assembly lines. You see how much time/how many samples were spent IN A FUNCTION
(and optionally on which Python line), not in which CPU instruction. In most
cases that is enough — a performance problem in application code can usually be
located at the function level.

---

## The GIL (global interpreter lock)

**Definition.** In the standard GIL-enabled CPython build used in this course,
only one thread at a time executes Python bytecode in the same interpreter.

**Intuition.** Think of a kitchen with one knife. Cooks can take turns chopping
Python bytecode, overlap their waits for the oven, or do work that needs no knife.
Native extensions that release the GIL can run computations concurrently.

**Why it matters.** The GIL simplifies access to shared interpreter state,
including reference counts. Free-threaded CPython uses several techniques to
manage that state, including local and shared reference counts. The course
uses the standard build. `py-spy top --gil --pid <PID>` filters observations
to threads holding the GIL (attaching to a running process needs suitable
permissions, see exercise 2). It leaves out waiting threads and native CPU work
that runs without the GIL, so it cannot quantify lock contention by itself.

**Common mistake.** Adding threads to speed up the pure-Python pixel loop in
`_sepia_naive`. In the course build the threads take turns executing bytecode.
Threads can still overlap blocking I/O — while one thread waits on a file or a
socket, another can run — and native code can run in parallel when it releases
the GIL. See `09a-concurrency-gil-asyncio.md` for the process-pool alternative.

---

## Reference counting and the generational garbage collector

**Definition.** CPython manages memory in two layers. The first layer:
**reference counting (refcounting)** — every Python object has a reference
counter (`ob_refcnt`) of its strong references. When you create a reference to
an object (an assignment, adding it to a list/dictionary), the counter goes up;
when a reference disappears (end of scope, `del`, overwriting a variable), the
counter goes down.
(This is the mental model; since 3.12 "immortal" objects such as `None` keep a
fixed count, and the interpreter skips some counter updates internally.)
When the counter drops to zero, the object is deallocated **immediately**,
deterministically — without waiting for any garbage collector "pass" (its memory
goes back to the allocator, not necessarily to the operating system). The second
layer: the **generational garbage collector (GC)** — an additional mechanism
that catches **reference cycles** (object A points to B, B points back to A —
refcounting will never bring their counters down to zero by itself, even though
nothing from the outside uses them any more). The GC tracks objects that can
participate in cycles, such as lists, dicts, class instances and many other
containers — not, for example, ints or strings. In the standard build of the
course versions (CPython 3.11–3.13 and 3.14.5+) it divides them into 3
generations (0 = youngest/checked most often, 2 = oldest/checked least often).
Newly tracked objects start in generation 0. Survivors of a collection can move
to an older generation; objects in the oldest generation stay there. Younger
generations are scanned more often, because statistically most objects die
young (the generational hypothesis). (CPython 3.14.0–3.14.4 shipped an
incremental GC without the middle generation; 3.14.5 restored the 3.13
behavior.)

**Intuition.** Refcounting is like counting the people who hold an umbrella
together — when the last person lets go, the umbrella falls at once (the object
is freed immediately). The GC is a separate cleaning crew that walks around the
room from time to time looking for groups of people holding each other's hands
in a circle, so that none of them formally "lets go" of anyone, and yet the
whole group is cut off from the rest of the room (unreachable from the outside)
— refcounting cannot detect this on its own, because the counters never drop to
zero.

**Why it matters.** The distinction between "refcount = 0 → freed immediately"
and "cycle → needs the GC" explains why some memory leaks in Python are subtle:
the code may look as if "nothing holds" the object, yet the object stays alive
because there is a reference somewhere you did not think of (e.g. in a global
container). This applies directly to `app/images.py::THUMBNAIL_CACHE` (flaw F1,
exercise 8): every entry in this dictionary is a live reference to thumbnail
data — the refcount of those bytes will NEVER drop to zero as long as the key
`(image_id, size)` sits in the dictionary, because the dictionary itself is
global and lives for the entire lifetime of the process. This is not a cycle
(the GC would not help here) — it is an ordinary, live reference that nobody
removes. More in `06a-cpython-memory.md`. A true leak of the same kind (flaw
F1b, exercise 9): an object built on every request that registers its method in
its constructor (`EVENTS.subscribe(self.on_progress)`) with the global event
bus — the bound method holds `self`, the bus holds the method, the module holds
the bus. You find out who holds the object with `gc.get_referrers` (it lists
direct referrers among GC-tracked containers — a debugging aid, not a full
reference graph); typical
sources of such leaks (registries and subscribers, closures in global lists,
`lru_cache` on a method, logging handlers added per request) are covered in
`06a-cpython-memory.md`.

**Common mistake.** "Python has no memory leaks, because it has a GC." The GC
reclaims only objects that are no longer reachable — groups held together just
by reference cycles (and whatever only those groups hold). It does not remove
objects that still have a live reference (such as an entry in a cache that grows
without bound). In Python code a "memory leak" most often means: "somebody
somewhere holds a reference longer than they should", not "the GC does not
work" (native allocations in C extensions are another possible source of
growth).

---

## The CPython memory allocator: pymalloc, arenas, pools

**Definition.** When a Python object is created, CPython does not ask the
operating system for memory every time — it uses its own allocator,
**pymalloc**, optimized for small allocation requests (up to 512 bytes each,
which covers most small objects: ints, short strs, tuples, small lists).
Pymalloc requests large blocks — **arenas** (1 MiB by default in 64-bit builds
of the course versions, 3.11–3.14) — from the OS, divides each arena into
**pools** (16 KiB; older or 32-bit builds use 256 KiB arenas and 4 KiB pools),
and each pool into **blocks** of a fixed size for a given size class. When
Python "frees" a small object (the refcount drops to zero), its pymalloc block
returns to its pool — but an arena can be returned to the operating system
(which can reduce the RSS of the process) only when the WHOLE arena is empty.
Larger requests (> 512 B) — such as the raw image bytes in `THUMBNAIL_CACHE` —
go to the system allocator (`malloc`); handing memory back to that allocator
does not necessarily lower the RSS.

**Intuition.** Imagine a rack of drawers ordered wholesale (an arena), divided
into compartments of one size (a pool), each of which holds one specific type of
item (blocks). When you take an item out (free an object), the compartment
becomes empty and ready for the next item of THE SAME size — but the whole rack
(the arena) goes back to the warehouse (the OS) only when ALL the compartments
on it are empty. If one compartment out of a thousand still holds one item, the
whole rack stays occupied.

**Why it matters.** RSS counts the process's resident pages, including pages
for memory that allocators can reuse. Live blocks can keep a pymalloc arena
mapped. Empty arenas backed by `mmap` can be unmapped, while blocks handed back
to `malloc` may remain reserved by that allocator. For exercise 8, look for
memory growth to level off under sustained comparable load, and verify the
cache's entry count directly.

**Common mistake.** Reading the RSS as the size of live Python objects.
`tracemalloc` reports the size and count of currently traced allocation blocks
by allocation site. Those blocks need not correspond one-to-one to cache
entries, and native allocations outside the tracing mechanism may be absent.
`sys.getsizeof()` reports an object's shallow size, excluding the objects it
references. See exercise 7 and `06a-cpython-memory.md`.

---

## Sampling profiler vs tracing profiler

**Definition.** A deterministic profiler such as `cProfile` observes call and
return events and aggregates counts and timings by function. The counts refer
to observed calls and the timings come from the instrumented execution. A
sampling profiler such as `py-spy` periodically captures stacks. Sample shares
estimate where the program spent time under the chosen sampling mode.

**Intuition.** Tracing is like logging each doorway crossing and totaling the
log. Sampling is like taking periodic snapshots of a room to estimate where
people spend their time.

**Why it matters.** Use `py-spy` or Pyroscope to find dominant costs under load
(exercises 1–2 and 4), and `cProfile` with SnakeViz for function call counts and
cumulative timing in a short run (exercise 3). In `pstats`, `tottime` excludes
time in subcalls and `cumtime` includes it; by default these are elapsed-time
measurements, not CPU time. Timing hooks can inflate the
apparent cost of code with many small calls. Sampling generally perturbs such
workloads less. Check overhead under representative load before relying on it.

**Common mistake.** Assuming either method is always more accurate. Brief
sampling can miss work. Tracing can distort timings through its own overhead.

---

## On-CPU, off-CPU and wall-clock and the limits of the profiler

**Definition.** **On-CPU time** is the time during which a thread ACTUALLY
executes instructions on the processor. **Off-CPU time** is the time during
which it does not — it is blocked (waiting for I/O, a lock, a timer) or ready to
run but not scheduled. An ideal **on-CPU profile** counts only on-CPU time. A
**wall-clock profile** counts the TOTAL elapsed time, including waiting time — a
thread blocked on `socket.recv()` or `time.sleep()` shows up in a wall-clock
profile as "spending time" in that call, even though the processor is doing
something completely different in the meantime (or nothing). A wall-clock
profile therefore includes both on-CPU time and off-CPU waiting time; it is not
the same thing as a pure off-CPU profile.

A sampling profiler such as the one in the Pyroscope client does not get these
times from the operating system scheduler — it periodically reads thread stacks
and decides which samples to keep. In the Pyroscope client (`pyroscope-io`
1.4.0, default py-spy-based implementation) two filters decide this:
`oncpu` (True = drop samples of threads the sampler detects as idle — a
heuristic, not scheduler accounting; False = keep them) and `gil_only` (True =
keep only threads holding the GIL; False = no GIL filter). The course uses two
presets: **cpu** = `oncpu=True, gil_only=True` (an approximation of on-CPU
Python work; native work that releases the GIL is left out) and **wall** =
`oncpu=False, gil_only=False` (both filters off, so waiting threads are kept as
well). In wall mode the samples of several threads add up, so their total is
not the duration of any single request. You choose the preset **once, at
process startup** (`PYROSCOPE_WALL=1`, once you have implemented exercise 11)
and label it with the
tag `mode=cpu|wall`; a repeated `configure()` in a running process is refused
(it returns `False` in 1.4.0) and changes neither the mode nor the tags, so
changing the mode means a restart.

**Intuition.** On-CPU is a stopwatch measuring only the time during which the
cook is actually chopping vegetables. Wall-clock is a stopwatch measuring from
the moment the cook starts the recipe to the moment they finish it — including
the time spent standing at the oven.

**Why it matters.** This distinction decides whether you will see a given
problem at all. In exercise 11 you add an artificial `time.sleep(2)` to an
`async def` endpoint (it blocks the event loop). In the controlled run described
there, with the `endpoint=fetch` filter, the cpu preset captured at most a few
samples from the code around the wait and no own samples of `fetch_image` (the
thread is sleeping, not computing), while in the wall preset the sleeping
`fetch_image` accounted for most of the self samples in that window. Flaw F2
(`_sepia_naive`), on the other hand, is clearly visible in both modes. Wall mode
has its price: **in the profile of the whole service idle waits can obscure
costs** (pool threads waiting in `Condition.wait`, the event loop waiting in
`select()`). Search by function name, or use the `endpoint` tag as a clue
rather than as a measurement of a request (see the tag limits below), and
measure latency separately. Exact shares depend on the machine, the load and
the time window — measure them yourself.

**The limits of the profiler (a summary; the full lesson is in exercise 11).**
- *Wall shows blocking calls on the thread that executes them.* A `sleep` in an
  `async def` sits on the event loop thread, so it is visible. But a coroutine
  **suspended** on an `await` is not on the active call stack of any thread, and
  the sampling profilers used here read only those stacks — waiting for a
  network response through an `await` does not show up as that coroutine's
  frames (at most you see the event loop in `select()`). You measure that kind
  of waiting with time: request latency (`curl -w '%{time_total}'`), timing in
  the application, or the `trace` extension in httpx for transport events.
- *Thread tags and `asyncio`.* `tag_wrapper` attaches the tag to the current
  **thread** for the duration of the block. `def` endpoints run in pool threads
  (shared over time, one request at a time per thread), so the tag marks the
  samples taken on that thread while the tagged block runs — not necessarily
  everything the request costs. `async def` handlers share a single event
  loop thread, so the tags of concurrent requests overlap: `endpoint=fetch` may
  contain other work on the loop thread (e.g. imports, other requests' frames)
  and idle waiting in `select()`. Do not treat the tag of an `async def`
  endpoint as an exact per-request breakdown.
- *`idle`.* Samples of idle threads (waiting for a task, for a timer) are not
  "load" — in wall mode you have to filter them out, in cpu mode the idle
  heuristic drops them.

**Common mistake.** Dismissing a slow endpoint because its CPU profile has few
samples. First check the scope and filters: the course's `gil_only=True` CPU
preset can miss native work that releases the GIL. Compare wall time with CPU
time for the same scope (`real` versus `user + sys` in `time`). In a controlled
single-threaded run a large gap suggests waiting or time off the CPU. Process
CPU time can add up across threads and exceed wall time. Use a wall profile to
investigate blocked threads and measure request latency for suspended awaits.

---

## Flame graph — how to read it

**Definition.** A flame graph is a visualization of a call-stack profile: every
horizontal **frame** is one function. The **Y** axis (vertical) is the **call
stack depth** — the higher, the deeper in the call chain (the function at the
bottom called the function above it, which called the next one, and so on). The
**X** axis (horizontal) is **NOT chronological time** — it is an aggregation of
samples, usually sorted alphabetically or by frequency, so that the same call
paths sit next to each other and add up into one wide frame. The **width of a
frame** is proportional to the number of samples in which the function was on the
stack — that is the right measure of "how much time/how many samples it cost",
with a distinction between **self time** (time/samples spent DIRECTLY in the
code of this function, not counting the functions it calls) and **total time**
(the self time of this function + the total time of all functions it called,
that is the full width of its frame, including the portions covered by
children). **Color** usually has NO semantic meaning — it is a random palette
for readability (to tell neighboring frames apart), although some tools can
color by module/package; the meaning of color depends on the tool and view, so
check the legend.

**Intuition.** It is a geological cross-section — the layers (Y) are the call
depth, the width of a layer (X) is how much "material" (samples) is there. The
width not covered by child frames is the function's self share — a wide frame
with nothing on top of it eats a lot of time itself (self time). A wide frame
near the bottom is usually just a root (`main`, the server, a thread) with a large
total and small self time. A tall, narrow "tower" = a deep call chain present in
a small share of samples.

**Why it matters.** Telling self time from total time is the core diagnostic
skill of this course. For flaw F2 (`_sepia_naive`) a flame graph under load will
show a VERY WIDE frame directly in that function (high self time — the
`for y / for x` loop itself eats the time, not the functions it calls). For flaw
F3a (a new HTTP client on every request, exercise 12), in the run described in
that exercise, with the cpu preset and the `endpoint=fetch` filter, the CPU
profile showed only a narrow trace — the client constructor
(`create_default_context`, `AsyncClient.__init__`) took a small share of
samples. Whether the real cost sits elsewhere (e.g. in opening new connections)
is a hypothesis you check with other measurements — connection counts,
latency, CPU per request — not something
a narrow frame proves. It is a good lesson: the width of a frame is a share of
the *samples* in the chosen time range, not of what hurts in the system. The
distinction between "where the problem actually sits" (self time) and "what is
expensive as a whole" (total time) determines WHAT you fix.

**Common mistake.** "The frame on the left of the flame graph ran BEFORE the
frame on the right." No — the X axis is not a time axis (it is not the same as a
Gantt timeline/trace). The horizontal order is a result of sorting (usually
alphabetical for frames on the same level), not of chronology. If you need a
time axis (e.g. "what happened in this second"), use a time-ordered view (e.g.
`py-spy record --format speedscope` or `chrometrace`) or narrow the time range
in Pyroscope before reading the flame graph. `py-spy dump` shows a single
snapshot of all stacks at one moment, not a timeline.

---

## Continuous profiling vs ad-hoc profiling

**Definition.** **Continuous profiling** (here: Pyroscope) is profiling that
runs continuously on a RUNNING application (e.g. in production or under the
load generator for its whole duration; this setup uses low-rate sampling), with
profiles collected, tagged (`tag_wrapper`, exercise 4) and stored in a backend
that lets you compare
periods over time (e.g. "the profile before the deployment" vs "the profile
after the deployment", exercise 15). **Ad-hoc profiling** is running a tool by
hand (`py-spy record`, `cProfile`, `memray run`) on demand, for a specific,
usually short run, to get a one-off, detailed report.

**Intuition.** Continuous profiling is a surveillance camera recording all the
time in the background, set up to cost little — it lets you "rewind" later and
see what happened at a given hour, or compare yesterday with today. Ad-hoc
profiling is taking out detailed measuring equipment for a moment to
investigate one specific incident here and now.

**Why it matters.** In this course Pyroscope (exercises 1, 4, 15) gives you a
continuous view of what happens under the load generator, and a mechanism for
comparing profiles over time (a performance regression between versions, F8,
exercise 15) — it is the "where to look in general" tool. Use the same profile
type and preset, comparable workloads and windows, and equivalent filters apart
from the difference under test. For a deployment regression, the application
version is the difference under test.
`py-spy` (exercise 2), `cProfile` + `snakeviz` (exercise 3), `tracemalloc`
(exercise 7) and `memray` (exercises 8–9) are ad-hoc tools — once you know from
Pyroscope that the problem is, say, in the `images.py` module, you reach for
them to get function-level timings and call counts or allocation details,
depending on the tool.

**Common mistake.** "Since I have continuous profiling, I need nothing else."
In this course Pyroscope collects only CPU/wall-clock stack samples — the
client's memory profiling (`mem_enabled` in `pyroscope-io`) stays at its
default, off — so it does NOT show memory (allocations, leaks) here, and it does
not give exact observed call counts as `cProfile` does. For memory you use
`tracemalloc`/`memray` (ad-hoc).

---

## How it all fits together (map)

```
CPython (standard build, with GIL) executes bytecode in the interpreter loop
        │
        ├─ GIL: one thread at a time executes bytecode ─────── 09a, ex. 10–11
        │
        ├─ memory: refcounting (immediate) + GC (unreachable cycles) ── 06a, ex. 7–9
        │        + pymalloc (arenas/pools) → RSS vs "freed"
        │
        └─ per-instruction overhead → a Python loop is slower
           than C code (Pillow/numpy) ─────────────────────────  04a, ex. 5–6

How you look at it:
        sampling (py-spy, Pyroscope)  vs  tracing (cProfile)
                    │                           │
            estimates from samples      observed call counts, instrumented timings
                    │
        on-CPU (computing)  vs  wall-clock (computing + off-CPU time) ── 11a, ex. 11–14
                    │       (Pyroscope presets cpu/wall: sample filters chosen
                    │        at startup, not scheduler accounting;
                    │        limits: await, tags in async)
                    │
              flame graph: Y=depth, X=aggregation (NOT time),
              full width=total, part not covered by children=self
                    │
        ad-hoc (py-spy/cProfile/tracemalloc/memray, by hand)
                    vs
        continuous (Pyroscope, always on, comparable over time) ── ex. 1, 4, 15
```

Now go on to `01.md` (Pyroscope setup) — the first block reading,
`04a-cpu-internals.md`, waits before exercises 5–6.
