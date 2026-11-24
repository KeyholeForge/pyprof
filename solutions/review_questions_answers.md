# solutions/review_questions_answers.md — answer key to the review questions

Look here AFTER your own attempt at answering the review questions of each
exercise (`exercises/01.md` … `16.md`).

## Exercise 1 — Setup and the first flame graph

1. The width of a frame = the share of samples (in the selected time window)
   in which the function appears at this point in the stack, including the
   functions it calls — not its duration and not the number of calls. A
   function called once that runs for a long time can have a narrower frame
   than a function called thousands of times for a short time, if the latter
   consumes more samples in total. In the course's CPU mode (`gil_only=True`)
   only threads holding the GIL are sampled, so it is a share of those
   samples, not of the whole CPU time of the process.
2. Because `pyroscope.configure()` starts the SDK client (among other things,
   the thread that collects samples and sends them to the server) — samples
   from before the configuration are simply not collected; there is no
   "backfilling" of a profile. Calling it at startup means the profile covers
   the traffic from the first request. For the same reason you choose the
   profiler mode (cpu/wall) at startup: calling `configure()` again while the
   agent is already running is refused (on `pyroscope-io` 1.4.0 it returns
   `False`, and the mode and tags stay the same).
3. The profile will be very "grainy" — at 1 Hz the profiler targets one
   sampling opportunity per second on average, so short requests (5 ms) are
   easily missed; with little traffic the shares are noisy and short code
   paths may be missing altogether. With more observations under a comparable
   workload, random noise may decrease — you just need far more of them.

## Exercise 2 — py-spy

1. `top` is a LIVE view, refreshed periodically, aggregating samples over time
   (like the system `top`); `dump` is a ONE-OFF snapshot of the stack of all
   Python threads at one exact moment.
2. `tracemalloc` works INSIDE its own process (Python instruments itself) — it
   does not need access to the memory of ANOTHER process. `py-spy` reads the
   memory of SOMEONE ELSE's process from the outside, and macOS allows that
   only to root (or a signed debugger) — hence `sudo`. SIP is a separate,
   additional block: even root cannot read SIP-protected binaries such as
   `/usr/bin/python3`. On Linux attaching by PID usually needs root as well,
   unless the system's ptrace policy and your permissions allow it (e.g.
   `CAP_SYS_PTRACE`, or `kernel.yama.ptrace_scope` set to 0). In a Linux
   container started with `--cap-add SYS_PTRACE`, py-spy works without
   `sudo` on processes of the same container.
3. In the filter phase loadgen draws `grayscale`, `blur` and `sepia` with equal
   odds for every request, so only about 1/3 of the draws are sepia (the image
   uploads before that phase are not filters). In this snapshot 3 of the 5
   busy worker threads had a `_sepia_naive` frame. That is consistent with the
   hypothesis that a sepia request holds a worker thread longer than the other
   filters, but it does not prove it: one snapshot is a single sample. Take a
   few more dumps during the traffic to see whether the pattern repeats;
   `py-spy top`, which skips idle threads by default, answers a different
   question (where the samples of the running code fall), not how many threads
   are busy. The snapshot does not tell you how much CPU sepia uses either —
   in CPython with the GIL only one of those threads can execute Python code at
   a time (a thread shown as `idle` may, for example, be waiting for the GIL),
   so they take turns rather than compute in parallel — and it gives you no
   request latencies or thread holding times; measure those separately.

## Exercise 3 — cProfile + snakeviz

1. cProfile records supported call events — the calls and returns of Python
   functions and of selected built-ins such as `min` (instrumentation) — and
   that bookkeeping costs time on
   every recorded call — the more tiny calls (like the 9 million `min` calls in
   the pixel loop), the bigger the overhead. It does not fall evenly on all
   functions, so even the proportions can get skewed. A sampling profiler only looks
   at the stack from time to time, so its overhead is usually much lower. The
   overhead matters whenever you read the timings rather than the call counts,
   and when profiling code in production under real load — there you rather use
   a sampling profiler (py-spy/Pyroscope); the time of a single function is
   benchmarked offline with `timeit`.
   Numbers from my run: the same image took about 0.7 s per call under the
   `timeit` command from exercise 6 and about 1.5 s under cProfile — a rough
   comparison, not a controlled measurement of the overhead.
2. `tottime(A)` is about 10% of `A`'s time (only the body of `A`, excluding
   `B`); `cumtime(A)` is 100% of `A`'s time (`A`'s own time plus the time in
   `B`). Measured against the whole profile, both numbers also depend on what
   else runs outside `A`.
3. Because the script enables the profiler only around the call to
   `_sepia_naive`: opening and decoding the JPEG and the RGB conversion happen
   before `enable()`, and there is no FastAPI/Starlette/HTTP layer (request
   parsing, middleware), no JPEG encoding of the response and no saving at all.
   In exercise 1, Pyroscope samples eligible stacks in the running service
   (CPU mode, GIL-holding threads), not just this function, so frames from
   that path (request handling, encoding the result, middleware) can appear in
   its flame graph when samples land in them — as a share of samples, not as a
   timing breakdown of a single request.

## Exercise 4 — Tagging and reading flame graphs

1. Different keys add up (a sample has both tags). The same key with a
   different value: in my first run (pyroscope-io 1.4.0; 3 × 4 s of CPU work,
   outer `k=outer`, inner `k=inner`) all ≈12.5 s of CPU went to `k=outer`, and
   `k=inner` got 0. Repeated runs did not give a stable winner: with the same
   nesting, ≈12 s landed on `k=inner` and 0 on `k=outer` (twice); in a variant
   with extra work outside the inner block, the samples went all to `k=outer`
   (once) or were split between the two values (twice). Which value a sample
   ends up under is undefined.
   The mechanism in the SDK: pyroscope-io 1.4.0 does not keep a stack of
   values. Entering a block adds a (thread, key, value) tag and leaving it
   removes that same tag, so inside the inner block the thread carries both
   `k=outer` and `k=inner` at once; nothing masks the outer value. Which of
   the two the stored profile ends up showing is what the runs above could
   not pin down.
   Conclusion: do not nest the same key; to distinguish layers, use different
   keys.
2. For a single frame, read its tooltip: **self** is the weight of samples
   ending at that frame (the function was executing its own code); **total**
   is the weight of samples passing through it, including its callees. On the
   flame graph, self is the part of the frame's width not covered by its
   children (the frames directly below it in Pyroscope). A large self means
   that a large share of the sampled CPU in this view was spent directly in the
   function's own code (one long call or many short ones — the profile does not
   say which), not that each call is slow; a large total with a small self
   means its children cover almost all of its width, so the cost lies deeper.
   The table groups the results by function, so for a function that appears in
   several places in the stack its row can differ from a single frame. The
   height of a frame is only a level of the stack, not a measure of cost.
3. Because one process serving many different routes mixes the costs of
   completely different operations in one profile — without tagging you cannot
   tell "this endpoint takes most of the CPU" from "another endpoint dominates
   the profile and hides the first one" on a shared, undivided flame graph.
   Tags split the profile by route; they show how the sampled CPU is
   distributed, not the latency of each request.
   Caveat: the tag is set per thread, so for `async def` endpoints (a shared
   event loop thread) the tags of concurrent requests get mixed — for `def`
   (a synchronous handler runs on a pool worker thread for its whole
   execution) they are reliable (exercise 11).

**Mini-incident (step 6) — what to expect.** Read this only after you have
written down your hypothesis. In my run, the CPU profile under
`endpoint=upload` showed `save_bytes` with about 11% of the self samples and
the multipart parser wider next to it (about 20%). These are observations from
my environment, not numbers you must reproduce, and not a like-for-like
comparison: one is the self share of a single function, the other the width
of a frame that includes its callees, and the parser share under the tag is
only approximate (step 6). To judge how much of the sampled CPU the
file-saving path accounts for, read its Total, including callees, in the
unfiltered `pixelforge` profile for the upload-only window. If that Total is
small, the CPU profile allows you to say that the CPU cost of the upload path
does not lie mainly in the file-saving code. What it cannot show:
`save_bytes` calls `os.fsync` after every chunk, and while the disk completes
the write the thread waits off the CPU — the profiler in CPU mode
(`oncpu=True`, `gil_only=True`) takes no samples of that waiting. CPU sampling
does not tell you how long the thread was blocked on `fsync` or whether that
wait caused the reported slowness; that needs a different measurement —
wall-clock mode in exercise 11 (in my run the same `save_bytes` had 59% there,
a share of wall-clock samples that cannot be compared 1:1 with shares from CPU
mode) and the disk exercise 14.
