# 04a. Reading: CPU internals

A reading, not an exercise — no tasks and no definition of done. Goal: build a
concept map before you start exercises 5–6 (Block B: CPU). Every concept follows
this pattern:

> **Definition** → **Intuition/analogy** → **Why it matters** → **Common mistake**

Come back here whenever things stop adding up. Short definitions of related
terms (bytecode, interpreter loop, GC, profilers) are in `glossary.md`.

---

## The cost of operations in Python: per-instruction interpreter overhead

**Definition.** In simplified terms, every bytecode instruction in CPython (for
example `BINARY_OP` for an addition or a list index, `LOAD_ATTR` for an
attribute access) goes through the cycle of the interpreter loop: fetch the
instruction, decode it, dispatch to the matching C code, update the value
stack. This dispatch overhead is paid again for every instruction, however
"simple" the operation is logically. Since 3.11 the adaptive interpreter
specializes hot instructions for the types it sees (and CPython 3.14 also
combines some pairs of instructions into one), which lowers the overhead but
does not remove it — and the work behind each instruction differs, so there is
no single cost per instruction. On top of that, Python values are objects:
adding two numbers means type checks and a result object, not just the
arithmetic. That is why adding two numbers in Python costs many times more CPU
cycles than the same addition in compiled C code.

**Intuition.** When you calculate by hand on a calculator, you have to press
several keys every time (interpretation), even for a trivial 2+2. A
spreadsheet with a ready-made vector formula (an analogy for a single call
into C code such as Pillow/numpy) does a thousand such additions in a single
command, without repeating the "key-pressing" overhead a thousand times.

**Why it matters.** This directly explains why a pure-Python loop over
millions of elements is much slower than a vectorized operation in a C
library ("vectorized" here means: the loop runs inside one call into compiled
code). Take `app/images.py::_sepia_naive` — for a large image from the
corpus (2000×1500 = 3,000,000 pixels) the function runs a DOUBLE Python loop,
with several dozen bytecode instructions per pixel (arithmetic, calls to `int`
and `min`, reading and writing the pixel). That is 3 million iterations of the
inner Python loop, each paying the interpreter's per-instruction overhead many
times. The fixed version, `img.convert("RGB", matrix=SEPIA_MATRIX)`, applies
the same math (the same 3×3 coefficients per pixel; the output channels can
differ by one level, because Pillow rounds while `_sepia_naive` truncates
with `int()`), but the WHOLE loop over pixels runs inside a single C call in
Pillow — the Python interpreter executes one method call, with a fixed number
of steps however many pixels there are, instead of 3 million loop iterations.
The large difference in execution time does not come from a "better
algorithm" (both visit every pixel once) — it comes from WHERE the loop
physically runs: in the Python interpreter, with all its per-pixel Python
work, or in compiled C code. A timing comparison of the two measures that
whole difference, not the dispatch overhead in isolation.

**Common mistake.** "Since C is faster, every Python loop has to be rewritten
by hand in C/Cython." Usually you do not need to write your own C — libraries
like Pillow, numpy and pandas already provide vectorized operations on typical
data structures (images, arrays, dataframes). The first step is always to
check whether an existing library has a ready-made high-level operation (like
`Image.convert` with a matrix) instead of writing a loop from scratch — only
when no such operation exists do you consider Cython/numba/C extensions.

---

## Algorithmic complexity and the profile

**Definition.** Algorithmic complexity (Big-O notation) describes how the
amount of work grows with the size of the input (an upper bound, for a stated
measure of input size and of work) — regardless of the language the algorithm
is implemented in. A profile (flame graph, `cProfile`) shows the ACTUAL
time/number of samples for a SPECIFIC run with a SPECIFIC data size — it is a
point measurement, not an asymptotic analysis.

**Intuition.** Complexity is a recipe ("if everyone greets everyone, N guests
need about N²/2 handshakes — the work grows like N²") — it tells you how the
work grows in theory. A profile is a stopwatch measured at a specific party
with a specific number of guests — it tells you how long it actually took NOW,
on THIS hardware, with THIS data.

**Why it matters.** A profile on its own will not tell you "this is O(n²)" — it
only shows that a given function is slow FOR THIS particular input. To tell
"slow because there is a lot of data and that is normal" apart from "slow
because of bad complexity", you have to compare the time of the function itself
(not of the whole request, which also has fixed costs) at several input sizes
(for example `_sepia_naive` on a small corpus image vs a large one) and see
whether the time grows roughly in proportion to the number of pixels (which is
expected — a filter has to touch every pixel at least once) or clearly faster.
Faster growth is a reason to check the code (for example for an accidentally
nested O(n²) loop where O(n) is enough) and the measurement conditions; the
timings alone do not prove the class — reading the code does. In this course
`_sepia_naive` is linear (O(width×height)): one pass over the pixels with a
fixed amount of work per pixel — the problem is not the complexity, it is WHERE
this linear loop physically runs (see above). Another example from this course:
string concatenation in a loop (`report += line`, exercise 9, ★ Bonus B). `str`
is immutable, so if each append copies the entire accumulated prefix and the
appended pieces are roughly the same length, the amount copied grows
quadratically with the number of pieces — O(n²) copying. CPython 3.14 has an
optimization (not a language guarantee): it can sometimes resize a local `str`
accumulator when the result of `s += x` goes straight back into the same
variable. Not sharing the string (no other reference to it) helps, but the
string's representation and other checks also matter, and a resize can still
move the buffer. The optimization does not apply to a global variable, an
attribute (`self.report += line`) or `bytes`, among other cases. So whether a
given loop really pays the quadratic cost depends on the code and the
interpreter — check it rather than assume it (exercise 9 ★). Whether such a cost
matters in the service is a separate question — answered by a profile of the
real workload, not by an isolated comparison. The lesson: complexity tells you
how the cost *grows*; the profile tells you whether it is *this* cost at all —
you have to check both before you start optimizing.

**Common mistake.** "This function has a lot of samples in the profile, so its
algorithmic complexity is bad." Not necessarily — a function can have optimal
complexity (linear, as it has to be, because it touches every pixel once) and
still be slow because it is implemented in pure Python instead of vectorized C
code. "A lot of samples" tells you WHAT is expensive, not WHY — that takes
additional reasoning (is it a linear loop in the wrong place, or really
O(n²)/O(n³)).

---

## Microbenchmark pitfalls

**Definition.** A microbenchmark is a measurement of the execution time of a
small piece of code, usually repeated many times, to judge "is version A faster
than version B". JavaScript in the browser runs on JIT engines that warm up over
time. CPython 3.14 can include an experimental JIT compiler; whether it is
available and enabled by default depends on the build. Even without an active
JIT, the first runs of a given piece of code are often slower than later ones,
for several reasons: one-time work (imports, first allocations, the adaptive
interpreter specializing instructions after the first few executions), the **CPU
cache** (data and instructions have to be brought from slower RAM into the fast
L1/L2/L3 cache for the first time) and the **disk/file system** (the first read
of an image file from the corpus may hit the physical disk, while later ones hit
the operating system's page cache — much faster). On top of that comes **system
noise**: other processes on the machine, OS thread scheduling. And in Python
specifically, the **garbage collector can fire DURING the measurement**: with
automatic cyclic GC enabled, enough net allocations of GC-managed (container)
objects (more allocations than deallocations since the last pass) can schedule a
collection, and if the collector runs during the timed interval, its work counts
towards the measured time. That work is triggered by allocations — often the
measured code's own — so it is not pure noise: it can be part of the real cost
of the code. `timeit` switches automatic cyclic GC off by default to make
timings comparable, which also hides this cost; if it belongs to what you want
to measure, switch it on explicitly and note that choice.

**Intuition.** Timing a single runner on a single day tells you nothing about
their average time — you have to time several runs (allowing for the first start
being slower because of warm-up) and look at the best/typical result, not a
single one — and ask why a slow run was slow: they might have had to stop and
retie a shoelace that their own running had loosened (GC — triggered by the
program's own work, so part of its real cost), or a headwind might have blown
(another process took the CPU).

**Why it matters.** In this course this applies directly to the CPU exercises
(5–6): when you compare `_sepia_naive` with the fixed version (`img.convert`
with a matrix), a single timing of one request can mislead you. The practice:
(1) take **many comparable repetitions** (the loadgen in this course fires many
requests in a row, not one; `timeit` repeats a snippet), (2) choose the
statistic for the question and keep all the times: the **minimum** (`timeit`
reports the best time per loop) is a low-noise estimate for an isolated snippet
— not proof that nothing interfered; the **median** shows the "typical" time,
robust against single anomalies; the **mean** is sensitive to a few slow
outliers (for example one request that hits a GC pass); if slow requests matter,
also look at a tail percentile, (3) decide whether you are asking about cold or
warmed-up behavior, and measure that state consistently (for warmed-up behavior:
discard the first runs, which may still be reading the file from disk or warming
up caches).

**Common mistake.** "I measured each version once and A is faster, so A wins."
A single measurement is noise and signal mixed together — without repetitions
you do not know whether the difference is real or accidental (for example the GC
happened to fire during the measurement of B). Profiling under a loadgen (as in
this course) gives you hundreds/thousands of stack samples instead of one
measurement — they show where the time went in that run more reliably, but
they do not replace repeated before-and-after comparisons. For manual
comparisons (for example `time` on a single curl) remember to repeat many
times.

---

## How it all fits together (map)

```
Per-instruction interpreter overhead (00-theory)
        │
        ├─ Python loop (_sepia_naive) ── slow not because of bad complexity,
        │                                 but because of WHERE it runs
        │
        ├─ vectorized C operation (Pillow) ── same math (rounding may differ
        │                                      by one level), loop inside a
        │                                      single call
        │
        └─ complexity (Big-O) ── a separate dimension: a linear loop in the
                                 wrong place (sepia) vs quadratic copying
                                 if each append copies the growing prefix
                                 (string +=; CPython can often avoid it —
                                 check, ex. 9 ★)

Measuring it:
        many comparable repetitions → min (isolated snippet) / median
        (typical request), keep all times; the mean is pulled by outliers
        watch out for: warm-up (CPU/disk cache, specialization), GC during
        measurement (off by default in timeit), OS noise
```

Now go to `05.md` (the exercise: profiling and fixing `_sepia_naive`).

---
