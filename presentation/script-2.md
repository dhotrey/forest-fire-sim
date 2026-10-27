# COSC3500 Milestone 1 — Presentation Script (target: 9.5 min)

Running time shown is cumulative. Practice with a timer once — if you're
consistently over, the easiest cuts are marked **[CUT IF SHORT ON TIME]**.

---

## S1 — Title (0:00 → 0:05)

Hello, my name is Aryan Dhotre, and this is my presentation for COSC3500 Milestone 1.

*(5s)*

---

## S2 — Forest fire cellular automaton (0:05 → 0:50)

The project I've chosen is a cellular-automaton-based forest fire simulation.
A cellular automaton is a grid of cells that evolves step by step, where each
cell's next state depends only on its current state and the state of its
neighbours.

The rules here are simple: a tree grows on an empty cell with probability p;
a tree ignites with probability f; a tree burns if any of its neighbours are
already on fire; and a burning cell becomes empty on the next step.

Figure 1 shows one timestep of that rule set, and on the right you can see it
running on a 300 by 300 grid for 500 timesteps, with p = 0.01 and f = 0.001.

*(~45s, cumulative 0:50)*

---

## S3 — Benchmarking methodology (0:50 → 1:50)

Before I get into the optimisations, let me quickly cover how I benchmark.

Everything is tracked in git, and I try to keep one optimisation per version
tag, from v0.0 up to v0.7. I compile each version at both -O1 and -O2 and time
it with `time`, taking the minimum of 5 runs per configuration to reduce noise
from the server. I test three grid sizes — 100², 500², and 10000² — mainly to
see the effect of cache size, though today I'll focus on the results from the
larger grids since that's where the differences are actually measurable.

All benchmarks for one version run inside the same Slurm job, so both
optimisation levels see the same node, same partition, same everything except
the compiler flag. Each job also logs the node's hardware and compiler info at
the start, so I can go back and sanity-check a result later. I also run a
warmup — first a trivial run to load the binary into the instruction cache,
then two full-scale untimed runs per grid size — so the first binary tested
isn't unfairly penalised with cold caches. And since the simulation depends on
random numbers, every run uses the same seed so results are deterministic and
comparable across versions. Each binary also prints its own build info —
version, compiler, flags — to stdout, which makes it much easier to tell log
files apart later.

*(~60s, cumulative 1:50)*

---

## S5 — v0.0: the baseline (1:50 → 2:35)

Let's look at the first version. This is deliberately just "make it work" —
no thought given to performance yet.

Something strange showed up immediately: on the cluster, which runs GCC 8.5,
the -O2 build was about 80% *slower* than -O1, consistently, across every grid
size — you can see that in the bar chart. That's backwards from what you'd
expect. I confirmed this wasn't a fundamental property of my code by testing
the same source on GCC 15 on my laptop, where -O1 and -O2 performed
comparably — so this looks like a GCC 8.5 code-generation issue specific to
this program.

*(~45s, cumulative 2:35)*

---

## S6 — v0.0: profiling with gprofng (2:35 → 3:10)

To dig into where the time was going, I ran gprofng on the -O1 build.
Running on -O2 wasn't useful here — the compiler had inlined the RNG straight
into `main`, so all the time just shows up against `main` with no breakdown.

On -O1 though, the picture was clear: the Mersenne Twister engine — `mt19937`
— accounted for 37% of total CPU time. Of a roughly 6-second run, 2 full
seconds were just generating random numbers. And this simulation doesn't need
statistically rigorous randomness —upon further research i discovered that mt19937 is well known to be slower than
modern PRNGs for what it offers here. So that became my first target: replace
it with something lighter.

*(~35s, cumulative 3:10)*

---

## S7 — v0.1: switching to pcg32 (3:10 → 3:40)

I moved to pcg32, a lightweight, high-performance PRNG. The effect was
immediate and large — you can see it in the chart, roughly a 46% improvement
at -O1 and a 73% improvement at -O2 on the 1000x1000 grid. And notably, the
-O1/-O2 anomaly from v0.0 disappeared: -O2 is now faster than -O1, as you'd
normally expect.

*(~30s, cumulative 3:40)*

---

## S8/S9 — v0.2: fixing cache access patterns (3:40 → 4:45)

Next I looked at memory access patterns. My grid was a vector of vectors, and
my loops were iterating in the wrong order relative to that layout — the
inner loop was jumping across separate heap allocations instead of walking
through one contiguous block. I just swapped the loop order so the inner loop
walks the contiguous elements within a single inner vector.

That one change took another 33% off the -O2 runtime. I confirmed the cause
with cachegrind: the L1 data cache miss rate dropped from 32.7% to 0.4% — a
roughly 80-times improvement — with raw D1 misses falling from about 1.38
billion to 16.5 million. So the hypothesis held: the original traversal order
was making very poor use of the L1 cache, and reordering it fixed almost all
of that. Last-level cache misses were basically unchanged between the two
versions, so this wasn't a silver bullet for every level of the hierarchy —
but for L1, it mattered a lot.

*(~65s, cumulative 4:45)*

---

## S10–S12 — v0.3: the "easy win" that wasn't (4:45 → 5:50)

For v0.3 I made what looked like an obvious optimisation: I was calling the
RNG unconditionally at the top of every cell update, even though a burning
cell or a tree with a burning neighbour never actually uses that random
number. So I moved the RNG calls inside the branches where they're actually
needed.

At -O1, this worked as expected — about 5–6% faster. At -O2, it made things
*worse* — around 17% slower. I used cachegrind's branch simulation to find
out why: v0.3 executed about 6% more instructions and 26% more branches than
v0.2, despite doing fewer RNG calculations overall. My conclusion is that at
-O2, GCC 8.5 had been able to treat the unconditional RNG call as a simple,
branchless, schedulable block of arithmetic. Making it conditional broke that
up — the RNG got inlined into multiple branches instead of one, and the
compiler lost the optimisation shape it had before. So more control flow,
even to do strictly less work, ended up costing more than it saved. I decided
not to chase that compiler interaction further and rolled the change back.

*(~65s, cumulative 5:50)*

---

## S13/S14 — v0.4: rollback plus integer thresholds (5:50 → 6:30)

v0.4 reverts the v0.3 change and adds a different, more reliable win: pcg32's
`nextFloat()` already calls `nextUInt()` internally and then converts that to
a float for the comparison. Since I only ever compare against a probability
threshold, I precompute `p_threshold` and `f_threshold` as integers once, and
compare directly against `nextUInt()` — skipping the float construction
entirely. Excluding the v0.3 detour, that gave an 8.4% speedup at -O2 over
v0.2, and about 24% at -O1, for a fairly small, low-risk change.

*(~40s, cumulative 6:30)*

---

## S15 — v0.5: 2D grid to 1D grid (6:30 → 7:25)

Next I flattened the grid from a vector-of-vectors into a single 1D vector.
Since this touches how every cell is addressed, correctness mattered a lot
here — so I computed a hash of the final grid state after 500 timesteps on
both the 2D and 1D implementations and confirmed they matched exactly before
trusting any benchmark numbers.

Cachegrind showed the 1D layout cut total data references roughly in
half — from about 3.7 billion down to 1.7 billion — mainly by removing the
extra heap allocations and pointer indirection of the vector-of-vectors
layout. Runtime-wise, that translated to about a 10% improvement at -O1, but
only about 2% at -O2 — because the original 2D layout's inner loop was
already reasonably cache-friendly after the v0.2 fix, so there wasn't much
locality left to gain. The win here was mostly about removing allocation
overhead, not cache behaviour.

*(~55s, cumulative 7:25)*

---

## S16 — v0.6 & v0.7: things that didn't work (7:25 → 8:25)

Not every idea paid off, and I think that's worth showing.

For v0.6 I manually simplified the array-index arithmetic in the flattened
grid — precomputing row start and end offsets instead of recomputing
`x * grid_size + y` every iteration. This produced no measurable
improvement, and was actually slightly slower at -O1. It turns out GCC was
already doing this exact strength-reduction automatically; my manual rewrite
just changed register allocation and instruction scheduling without
improving on what the compiler had already found.

v0.7 was a bigger swing: packing each cell into 2 bits instead of a full byte,
so four cells share one byte, cutting the grid's memory footprint to a
quarter. I verified correctness the same way as v0.5 — matching hashes
against the reference run — so the logic itself was sound. Cachegrind
confirmed the intended effect: D1 miss rate dropped from 0.9% to 0.1%, and raw
misses fell by about 75%. But total instructions executed roughly doubled,
because every single read and write now needs a shift and a mask to get at
the right 2-bit field. That overhead outweighed the cache benefit — v0.7
ended up around 50% slower than v0.5 at both 500² and 1000², at both
optimisation levels. It's a nice echo of the v0.3 result: fewer memory
accesses and fewer misses don't automatically mean a faster program if the
per-access cost goes up enough. I've kept both changes out of the version I'm
carrying forward to Milestone 2.

*(~60s, cumulative 8:25)*

---

## Reflection and next steps (8:25 → 9:00)

Looking back, the biggest lesson from this milestone is that intuition about
what "should" be faster doesn't always survive contact with a real compiler
and a real cache hierarchy — the RNG-conditional change and the 2-bit packing
both looked like clear wins on paper and weren't, while the loop-reorder fix
and dropping mt19937 were bigger wins than I expected. If I did this again
I'd reach for cachegrind and gprofng earlier, before trying an optimisation,
rather than after being surprised by the numbers.

For Milestone 2, the plan is to parallelise this — the update rule is
embarrassingly parallel across cells, which should make it a good fit for
OpenMP, and possibly a GPU implementation given the regular grid structure.

*(~35s, cumulative 9:00)*

---

## Buffer

That leaves roughly 30–45 seconds of slack against the 10:00 hard cutoff for
pacing, breath, and any stumbles — don't try to fill it; stopping at 9:00–9:20
is fine.

**[CUT IF SHORT ON TIME]**: if you're running long, the safest trims are (a)
the last two sentences of S3 about the startup banner/build-info printout,
and (b) shortening the v0.6 half of S16 to one sentence ("no measurable
improvement — GCC was already doing the same strength reduction") so v0.7 gets
more room, since v0.7 is the more interesting result.s
