# v0.0

This is the baseline. This is how the code came to me in my dream and I've just recreated it in main.cpp without any additonal thought. The idea is to just make the simulation work first and successive versions will work on making it faster.

## Observations:

Something very strange is happening. When this is compiled with GCC 15 , the o1 and o2 results are roughly similar but GCC 15 is only available on my laptop and on rangpur we have GCC 8.x and there o2 is ~80% slower than o1. The results are in data/v0.0/benchmarking/benchmarks-o1-o2.csv

Also asked about it on edstem - https://edstem.org/au/courses/38439/discussion/3524615

optimisations aside, i ran gprofng on the code with o1 [results](data/v0.0/gprofng/o1.txt) and found that the RNG eats 37% of the runtime

```txt

Excl. Total   Incl. Total    Name
CPU           CPU
 sec.      %   sec.      %
6.114 100.00  6.114 100.00   <Total>
3.823  62.52  6.114 100.00   main
2.292  37.48  2.292  37.48   std::mersenne_twister_engine<unsigned long, 32ul, 624ul, 397ul, 31ul, 2567483615ul, 11ul, 4294967295ul, 7ul, 2636928640ul, 15ul, 4022730752ul, 18ul, 1812433253ul>::operator()()
0.      0.    6.114 100.00   __libc_start_main
```

This is unacceptable. in the next version im going to fix the rng.

ref: https://edstem.org/au/courses/38439/discussion/3524615

# v0.1

found this library to generate prng https://github.com/wjakob/pcg32, it has an optimised SIMD / AVX version as well that i can use for milesone 2.

After switching out the heavy rng library to the pcg32 one v0.1 at o1 optimisation runs in 3.28s for 1000x1000 grid. for comparison in v0.0 this was at 6.10s so this one change has almost slashed the runtime in half.

# v0.2

This was an easy one, i was accessing the cpu cache NOT in a spacial and temporally favourable manner
I changed this from

```cpp
  for (int y = 1; y < grid_size - 1; ++y) {
    for (int x = 1; x < grid_size - 1; ++x) {
        auto r = rng.nextFloat();
        switch (grid[x][y]) {
```

to

```cpp
for (int x = 1; x < grid_size - 1; ++x) {
  for (int y = 1; y < grid_size - 1; ++y) {
        auto r = rng.nextFloat();
        switch (grid[x][y]) {
```

this little change took my runtime from 2.78s to 1.86s for 1000x1000 grid at o2 optimisation level

D1 miss rate collapsed from 32.7% → 0.4%

the loop-order fix (x,y → y,x) workied exactly as hoped:

| Metric          |                        v0.1 |                     v0.2 |      Change |
| --------------- | --------------------------: | -----------------------: | ----------: |
| D1 miss rate    | 32.7% (27.3% rd / 50.0% wr) | 0.4% (0.3% rd / 0.8% wr) | ~80× better |
| D1 misses (raw) |               1,380,045,198 |               16,451,695 |  ~84× fewer |
| Read misses     |                 880,009,705 |                8,416,206 | ~105× fewer |
| Write misses    |                 500,035,493 |                8,035,489 |  ~62× fewer |

more data at data/cachegrind/cache-test-v0.1-v0.2

# v0.3

This is a minor change, but i suspect it could have a significant impact on the performance. I'm cutting down the rng to only when it's needed. Basically now rng only happens when a the grid is empty or if a tree has none of it's neighbours burning.

silly ol me thought it would be this easy lmao. Turns out the performance on o2 actually got WORSE with this change, while o1 was better. But first some numbers

- 1000², v0.2 `-O2` averages 1.86 s; v0.3 averages 2.178 s: 17.1% slower
- At 500², it is similarly 17.8% slower.
- Curiously v0.3 -01 is about 6% faster.

Hypothsis :
In v0.2, RNG generation is unconditional and appears once: READ LAST SOL MESSAGE ON SLURM BENCHMARK ANOMALY CHAT

```83:104:main.cpp
auto r = rng.nextFloat();
// ...
} else if (r < f) {
```

In v0.3, it appears on two conditional paths:

```84:105:main.cpp
case CellState::Empty:
  if (rng.nextFloat() < p) {
// ...
if (rng.nextFloat() < f) {
```

At `-O2`, `nextFloat()` will be inlined—it is only a few operations in `pcg32.h`. Therefore

Therefore, this change:

1. Duplicates the inlined RNG sequence in the loop’s control-flow graph.
2. Makes advancement of the RNG state dependent on unpredictable cell-state branches.
3. Removes the opportunity to overlap unconditional RNG arithmetic with grid loads and state dispatch.
4. Saves RNG work only for burning cells and trees adjacent to fire, which may be a relatively small fraction of updates.

## Results and conclusion

The mean user times from the Slurm benchmarks were:

|  Grid | Build      | Mean user time | Change from v0.2 |
| ----: | ---------- | -------------: | ---------------: |
|  500² | v0.2 `-O1` |        0.666 s |         baseline |
|  500² | v0.3 `-O1` |        0.630 s |      5.4% faster |
|  500² | v0.2 `-O2` |        0.460 s |         baseline |
|  500² | v0.3 `-O2` |        0.542 s |     17.8% slower |
| 1000² | v0.2 `-O1` |        2.688 s |         baseline |
| 1000² | v0.3 `-O1` |        2.518 s |      6.3% faster |
| 1000² | v0.2 `-O2` |        1.860 s |         baseline |
| 1000² | v0.3 `-O2` |        2.178 s |     17.1% slower |

Cachegrind branch simulation for the 1000² grid, 500 timesteps, `p=0.02`
and `f=0.01` gave:

| Metric                 |     v0.2 `-O2` |     v0.3 `-O2` |                 Change |
| ---------------------- | -------------: | -------------: | ---------------------: |
| Instruction references | 15,306,357,873 | 16,221,531,044 |                  +6.0% |
| Branches               |  1,872,193,132 |  2,359,083,727 |                 +26.0% |
| Mispredictions         |    159,425,716 |    168,173,217 |                  +5.5% |
| Misprediction rate     |           8.5% |           7.1% | -1.4 percentage points |

The lower misprediction rate in v0.3 is misleading because it executes many
more branches: there are 486,890,595 additional branches and 8,747,501
additional mispredictions. The branch-prediction accuracy per instruction is
almost unchanged, so worse prediction accuracy by itself is unlikely to be the
main cause.

There are 500,000,000 cell updates in this test, so the increase is about 0.974
extra branches per update. The likely explanation is that making RNG
advancement conditional complicated the hot loop enough that GCC 8.5 `-O2`
could no longer apply the same branchless if-conversion and instruction
scheduling that it used for v0.2. Duplicated inlined RNG paths and additional
control dependencies may also contribute. At `-O1`, the benefit of skipping
some RNG work remains visible; at `-O2`, it is outweighed by 6% more executed
instructions and 26% more dynamic branches.

Skipping RNG calls also shifts the random-number sequence assigned to later
cells, so the two versions do not follow identical stochastic trajectories.
This means the Cachegrind evidence strongly suggests a GCC 8.5 code-generation
interaction, but does not prove one exact compiler transformation.

Conclusion: this conditional-RNG change is not an optimisation for the target
GCC 8.5 `-O2` build. v0.2 remains the fastest overall, and I am moving on to
more direct optimisations rather than investigating this compiler interaction
further. Full results and methodology are in
[`data/v0.3/branch-predition.md`](../data/v0.3/branch-predition.md).

# v0.4

Since the previous change resulted in a perf deg. 0.4 will roll this back. Along with that. Also i'll do an integer threshold compare instead of float.
The change has been rolled back and performance has been restored to #v0.2 levels.
Next I'm going to work port the rng to output an int32 instead of a float32. basically precompute `p_threshold`/`f_threshold`, compare against `nextUInt32()` directly. I believe this will save me time because nextfloat function internally calls nextint32 anyways. So I can just save on that.

The latest v0.4 benchmark used 500 timesteps, two warm-up runs, and five timed repetitions for each grid size. The 100² runs are too short to be meaningful: both builds complete in about 0.02 seconds, so timer and system noise dominate. The utility doesn't provide enough resolution for a sample size this small.

For the larger grids, the mean user times were:

|  Grid | v0.2 `-O1` | v0.4 `-O1` |       Change | v0.2 `-O2` | v0.4 `-O2` |      Change |
| ----: | ---------: | ---------: | -----------: | ---------: | ---------: | ----------: |
|  500² |    0.666 s |    0.560 s | 15.9% faster |    0.460 s |    0.426 s | 7.4% faster |
| 1000² |    2.688 s |    2.248 s | 16.4% faster |    1.860 s |    1.710 s | 8.1% faster |

The v0.4 `-O2` build is still about 24% faster than its `-O1` build at both
larger grid sizes. The improvement over v0.2 is consistent with the two v0.4
changes: rolling back the conditional-RNG change restores the simpler hot loop,
and comparing `nextUInt()` directly against precomputed integer thresholds
avoids the float construction and conversion work in `nextFloat()`.

# v0.5

for this one i think im going to change the implementation of the CA grid from a 2d grid to a 1d grid and will access it as such. reduce the data that's being fetched from RAM to cache? improve cache locality ? also would reduce heap allocs as a now it's just a vec instead of a vec of vecs

To do this properly i need to figure out a way to hash the final grid state so that i can perform a correctness check once the migration has been done.

The 1D port produced the expected final-state hash for a 1000² grid after
500 timesteps with `p=0.02` and `f=0.01`, so the migration preserved the
simulation result:

```text
15213144908148633160
```

The benchmark used the same setup as v0.4: 500 timesteps, two warm-up runs,
five timed repetitions, one pinned CPU, and GCC 8.5 on the same cluster node.
The intended effect was to remove the indirection and allocation overhead of
the vector-of-vectors representation. It achieved roughly a 10% speedup at
`-O1` and roughly a 2% speedup at `-O2` for both the 500² and 1000² grids. The
100² result was unchanged, but those runs are too short to compare reliably
because the timing resolution is only 0.01 seconds.

The original 2D layout stored the outer vector and each inner vector
separately, requiring a separate heap allocation for each column's cell
storage. The 1D layout uses one vector and therefore one contiguous heap
allocation per grid, removing the outer-vector indirection and the many small
allocations. The vector objects themselves are local to `main`, but their cell
storage is still heap-allocated; this change does not move the grid onto the
stack.

The original layout was already reasonably cache-friendly because the inner
`y` loop walked contiguous elements inside each inner vector. The 1D port
therefore does not fundamentally change the neighbor access pattern. At
`-O2`, the compiler can likely eliminate much of the nested-vector access
overhead, leaving the neighbor loads, branches, RNG, and state updates as the
dominant costs.

Cachegrind confirmed that the 1D layout reduces memory traffic, but not the
cache miss rate. For the 1000², 500-timestep `-O2` run, data references fell
from 3.72 billion to 1.73 billion (53% fewer), while D1 misses fell only from
16.45 million to 15.73 million (4.4% fewer). The D1 miss rate increased from
0.4% to 0.9% because there were fewer total references. This suggests that
the speedup comes mainly from removing vector indirection and allocation
overhead, rather than a major improvement in cache locality. Full results are
in [`data/v0.5/cachegrind/`](../data/v0.5/cachegrind/).

# v0.6

For this version I applied induction-variable simplification to the flattened grid traversal. Instead of calculating `x * grid_size + y` in the inner loop, the loop calculates the start and end of each row once and increments a single `index` variable through the contiguous interior cells. I applied the same
indexing to `hash1d_grid`.

The 1D grid hash was checked against the known reference case of a 1000² grid, 500 timesteps, `p=0.02`, and `f=0.01`. The resulting hash was `15213144908148633160`, so the rewrite preserved correctness.

The benchmark was run with the same setup as v0.5: five timed repetitions, 500 timesteps, one pinned CPU, GCC 8.5.0, and an AMD EPYC 7542 node. The results did not show a speedup:

|  Grid | Build | v0.5 mean user time | v0.6 mean user time |     Change |
| ----: | :---: | ------------------: | ------------------: | ---------: |
|  500² |  O1   |             0.500 s |             0.520 s | ~4% slower |
|  500² |  O2   |             0.418 s |             0.418 s |  unchanged |
| 1000² |  O1   |             2.016 s |             2.136 s | ~6% slower |
| 1000² |  O2   |             1.668 s |             1.688 s | ~1% slower |


The surprising result is explained by the difference between source-level
operations and generated machine instructions. Although the original source
spelled out a multiplication and addition for every cell, GCC can recognize
that `x * grid_size` is invariant within the inner loop and reduce the
expression automatically. The original loop was therefore likely already
using an induction variable in the optimized executable. The manual rewrite
expresses the same optimization, but changes register allocation, loop
comparison, branch layout, and instruction scheduling. GCC 8.5 generated
slightly worse `O1` code for the new loop. At `O2`, both binaries had the same
text size, which is consistent with the compiler optimizing both versions to
essentially the same result.

This change did not alter the memory access order or neighbor access pattern,
so it was a CPU instruction/code-generation experiment rather than a cache
locality optimization. Conclusion: induction-variable simplification did not
produce a measurable benefit for this workload and should not be counted as a
successful optimization without further assembly or performance-counter
evidence. Full benchmark data is in
[`data/v0.6/benchmarking/`](../data/v0.6/benchmarking/).
