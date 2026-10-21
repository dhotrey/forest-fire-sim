# Memory layout, SIMD, AVX and OpenMP

A working reference for the forest-fire simulation and the matrix-multiplication assignment.

**Last checked:** 15 September 2026. Based on the five linked discussions, the current forest-fire source, existing project notes, and the supplied assignment PDF and headers. MPI and CUDA have reserved sections for later study.

This is organised by concept rather than conversation date. Read sections 1–4 for the memory model, 5–7 for vectorisation, 8–12 for OpenMP, then 13–15 to apply them. Code marked **standalone example** is teaching code; other snippets illustrate a construct or an inner loop. Assignment restrictions are collected separately in section 14.

## Contents

1. [The big picture](#1-the-big-picture)
2. [Addresses, arrays and storage](#2-addresses-arrays-and-storage)
3. [Caches, locality and bandwidth](#3-caches-locality-and-bandwidth)
4. [Matrix multiplication and blocking](#4-matrix-multiplication-and-blocking)
5. [SIMD and AVX fundamentals](#5-simd-and-avx-fundamentals)
6. [Alignment, allocation and aliasing](#6-alignment-allocation-and-aliasing)
7. [Vectorisation patterns and complex numbers](#7-vectorisation-patterns-and-complex-numbers)
8. [OpenMP teams and work distribution](#8-openmp-teams-and-work-distribution)
9. [Who owns each variable?](#9-who-owns-each-variable)
10. [Synchronization and reductions](#10-synchronization-and-reductions)
11. [Single, master, sections and tasks](#11-single-master-sections-and-tasks)
12. [OpenMP SIMD](#12-openmp-simd)
13. [Applying this to the forest-fire simulation](#13-applying-this-to-the-forest-fire-simulation)
14. [Applying this to the matmul assignment](#14-applying-this-to-the-matmul-assignment)
15. [Building, measuring and checking correctness](#15-building-measuring-and-checking-correctness)
16. [Quick reference and common misconceptions](#16-quick-reference-and-common-misconceptions)
17. [MPI — reserved for later](#17-mpi--reserved-for-later)
18. [CUDA — reserved for later](#18-cuda--reserved-for-later)
19. [Sources and local reading map](#19-sources-and-local-reading-map)

## Concept index

Jump directly to a concept or example:

- **Addresses and storage:** [A pointer is an address with a type](#21-a-pointer-is-an-address-with-a-type) · [Flattening a two-dimensional array](#22-flattening-a-two-dimensional-array) · [Flat vector, native array and nested vector](#23-flat-vector-native-array-and-nested-vector) · [Array of structures versus structure of arrays](#24-array-of-structures-versus-structure-of-arrays)
- **Cache and memory behaviour:** [Memory hierarchy](#31-memory-hierarchy) · [Spatial and temporal locality](#32-spatial-and-temporal-locality) · [Loading, storing and eviction](#33-loading-storing-and-eviction) · [Latency, bandwidth and arithmetic intensity](#34-latency-bandwidth-and-arithmetic-intensity) · [False sharing and actual sharing](#35-false-sharing-and-actual-sharing) · [A little further: pages, prefetching and NUMA](#36-a-little-further-pages-prefetching-and-numa)
- **Matmul and blocking:** [What `i`, `j` and `k` mean](#41-what-i-j-and-k-mean) · [`ijk`: finish one output element](#42-ijk-finish-one-output-element) · [`ikj`: apply one A value across an output row](#43-ikj-apply-one-a-value-across-an-output-row) · [The six loop orders](#44-the-six-loop-orders) · [Blocking: restrict the working set](#45-blocking-restrict-the-working-set) · [A safe blocked OpenMP baseline](#46-a-safe-blocked-openmp-baseline) · [Choosing a tile and going further](#47-choosing-a-tile-and-going-further)
- **SIMD basics:** [SIMD is lane-wise work](#51-simd-is-lane-wise-work) · [The types and instruction families](#52-the-types-and-instruction-families) · [Load, operate, store](#53-load-operate-store) · [Tail handling](#54-tail-handling)
- **Alignment and pointers:** [Alignment refers to the starting byte address](#61-alignment-refers-to-the-starting-byte-address) · [Allocation choices](#62-allocation-choices) · [Aligned versus unaligned AVX access](#63-aligned-versus-unaligned-avx-access) · [Base alignment does not imply alignment of every row](#64-base-alignment-does-not-imply-alignment-of-every-row) · [Pointer reinterpretation is not a load](#65-pointer-reinterpretation-is-not-a-load) · [Aliasing also matters without casts](#66-aliasing-also-matters-without-casts)
- **Vector patterns and complex arithmetic:** [Choose the amount of control you need](#71-choose-the-amount-of-control-you-need) · [Broadcast and row updates](#72-broadcast-and-row-updates) · [Fused multiply-add](#73-fused-multiply-add) · [Reductions across lanes](#74-reductions-across-lanes) · [Masks, comparisons and branchless selection](#75-masks-comparisons-and-branchless-selection) · [The assignment uses complex floats](#76-the-assignment-uses-complex-floats)
- **OpenMP execution:** [`parallel`: every team member runs the block](#81-parallel-every-team-member-runs-the-block) · [`for`: distribute iterations across an existing team](#82-for-distribute-iterations-across-an-existing-team) · [Thread controls worth knowing](#83-thread-controls-worth-knowing) · [static / dynamic / guided / runtime scheduling](#84-scheduling-how-iterations-are-assigned) · [`collapse`: expose more logical iterations](#85-collapse-expose-more-logical-iterations)
- **Variable ownership:** [shared / private / firstprivate / lastprivate](#91-data-sharing-clauses) · [Local scratch and default(none)](#92-prefer-obvious-local-scratch-and-explicit-sharing) · [A private pointer is not a private allocation](#93-a-private-pointer-is-not-a-private-allocation) · [`lastprivate` means logical order](#94-lastprivate-means-logical-order) · [`thread_local`, OpenMP private and RNG state](#95-thread_local-openmp-private-and-rng-state)
- **Synchronization:** [Why `sum += value` races](#101-why-sum--value-races) · [Atomic operations](#102-atomic-operations) · [Atomicity versus memory ordering](#103-atomicity-versus-memory-ordering) · [`critical`: one participant at a time](#104-critical-one-participant-at-a-time) · [`barrier`: wait for the team](#105-barrier-wait-for-the-team) · [`nowait`: remove an unnecessary barrier](#106-nowait-remove-an-unnecessary-barrier) · [Reduction: local accumulation, then combine](#107-reduction-local-accumulation-then-combine)
- **Single, sections and tasks:** [`single`, `master` and `masked`](#111-single-master-and-masked) · [`sections`: a few different independent jobs](#112-sections-a-few-different-independent-jobs) · [task / taskwait / taskgroup / depend](#113-tasks-work-scheduled-onto-workers) · [Relation to Go and IPC](#114-relation-to-go-and-ipc)
- **OpenMP SIMD:** [`simd` versus `parallel for simd`](#121-simd-versus-parallel-for-simd) · [SIMD reduction](#122-simd-reduction) · [aligned / simdlen / safelen / linear / declare simd](#123-useful-simd-clauses)
- **Forest-fire implementation:** [What the current implementation actually does](#131-what-the-current-implementation-actually-does) · [Double buffering defines a synchronous update](#132-double-buffering-defines-a-synchronous-update) · [Two-bit packing changes the ownership unit](#133-two-bit-packing-changes-the-ownership-unit) · [A simple byte-grid teaching example](#134-a-simple-byte-grid-teaching-example) · [RNG choices and reproducibility](#135-rng-choices-and-reproducibility) · [Keep a team alive across timesteps](#136-keep-a-team-alive-across-timesteps) · [A practical forest-fire optimisation sequence](#137-a-practical-forest-fire-optimisation-sequence)
- **Matmul assignment:** [Verified assignment context](#141-verified-assignment-context) · [Rules that affect implementation choices](#142-rules-that-affect-implementation-choices) · [What an initial CPU implementation should establish](#143-what-an-initial-cpu-implementation-should-establish) · [A staged optimisation path](#144-a-staged-optimisation-path) · [Numerical validation and the GradeBot metric](#145-numerical-validation-and-the-gradebot-metric) · [Cluster-aware testing](#146-cluster-aware-testing)
- **Builds and validation:** [Build flags and their meanings](#151-build-flags-and-their-meanings) · [Check whether vectorisation actually happened](#152-check-whether-vectorisation-actually-happened) · [Time the relevant work](#153-time-the-relevant-work) · [Speedup and scaling](#154-speedup-and-scaling) · [Correctness cases that expose the common mistakes](#155-correctness-cases-that-expose-the-common-mistakes)
- **At-a-glance lookup:** [Choose by the problem in front of you](#161-choose-by-the-problem-in-front-of-you) · [Corrections worth remembering](#162-corrections-worth-remembering)

For new topics later: [MPI](#17-mpi--reserved-for-later) · [CUDA](#18-cuda--reserved-for-later).

---

## 1. The big picture

There are three mostly separate questions:

1. **Where is the data, and in what order do we visit it?** Layout, locality, loop order, blocking.
2. **How many elements can one instruction process?** SIMD, including x86 AVX.
3. **How many workers can process independent work?** OpenMP threads and tasks.

```text
One process, with shared arrays in its address space
    |
    +-- OpenMP worker 0 --> its assigned rows/tiles --> SIMD arithmetic
    +-- OpenMP worker 1 --> its assigned rows/tiles --> SIMD arithmetic
    +-- OpenMP worker 2 --> its assigned rows/tiles --> SIMD arithmetic
    +-- OpenMP worker 3 --> its assigned rows/tiles --> SIMD arithmetic
                              |
                     registers <--> caches <--> DRAM
```

The drawing is conceptual: threads are scheduled on hardware cores; caches may be private or shared depending on the CPU. A thread is not itself a core. Simultaneous multithreading can expose multiple logical CPUs per physical core, which share execution resources.

| Technique | What it changes | What it does not guarantee |
|---|---|---|
| Flat storage | Where neighbouring elements live | A good traversal order |
| Loop interchange | Order of accesses | Enough reuse for a large problem |
| Cache blocking | How much data is reused before moving on | A particular SIMD instruction |
| SIMD | Several data lanes per operation | Eight times the whole-program speed |
| OpenMP threads | Several workers execute concurrently | Race freedom or useful scaling |
| OpenMP tasks | Runtime scheduling of pieces of work | Go-style channels |

A productive progression is: correct serial algorithm → suitable layout/traversal → measure → improve reuse → vectorise independent work → distribute it across threads → measure again. The order can vary; each change needs a reason.

For matmul, reuse can make arithmetic throughput the bottleneck. For a grid update, memory traffic, random-number generation, branches or bit extraction might dominate. **Measure which limit applies to the version you actually have.**

## 2. Addresses, arrays and storage

### 2.1 A pointer is an address with a type

For `float* p`, `p + 1` advances by `sizeof(float)` bytes. On the x86 targets used in these examples, a float is 4 bytes:

```text
p       -> byte address 0x1000 -> p[0]
p + 1   -> byte address 0x1004 -> p[1]
p + 7   -> byte address 0x101C -> p[7]
```

`p[i]` means `*(p + i)`. The pointer does not carry a length. Accessing outside the allocated object is invalid even if the address happens to be mapped.

Heap allocation provides storage whose lifetime you manage; local automatic arrays usually use the stack. Either can be contiguous and cached. Heap storage is not inherently slow to access once allocated. Large matrices usually need dynamic allocation because stack space is limited.

### 2.2 Flattening a two-dimensional array

For a row-major `rows × cols` matrix:

```cpp
index = row * cols + col;
```

If rows include padding, use a **leading dimension**, `ld`, meaning the physical distance in elements from one row start to the next:

```cpp
index = row * ld + col;  // ld >= logical column count
```

For a compact `3 × 4` matrix:

```text
Coordinates:                  Flat indices:
(0,0) (0,1) (0,2) (0,3)        0  1  2  3
(1,0) (1,1) (1,2) (1,3)        4  5  6  7
(2,0) (2,1) (2,2) (2,3)        8  9 10 11

Memory: [row 0][row 1][row 2]
```

Moving one column: `+1` element. Moving one row: `+ld` elements.

For column-major storage, the formula is `col * ld + row`, with `ld` the physical column length. Neither convention changes the mathematical matrix; it changes which traversal is contiguous.

Use a sufficiently wide index for allocation sizes and address products:

```cpp
std::size_t index = static_cast<std::size_t>(row) * ld + col;
```

Casting after `row * ld` is too late if that multiplication already overflowed an `int`.

### 2.3 Flat vector, native array and nested vector

| Storage | Contiguous? | Useful distinction |
|---|---|---|
| `float a[R][C]` | All elements, in row-major order | Native nested arrays; dimensions normally known at compile time |
| `std::vector<float> a(R*C)` | All float elements | Owns storage; `.data()` exposes a pointer |
| `std::vector<std::vector<float>> a` | Each individual row | Rows are separate allocations; the whole matrix need not be contiguous |
| `float** a` | Not guaranteed | Could point to separate rows or a deliberately constructed backing allocation |
| `std::vector<bool>` | Special packed representation | Not an ordinary array of independently addressable bool objects |

Do not reinterpret a `float**` as a flat `float*`. The first contains pointers, not the matrix elements themselves. For native multidimensional arrays, retain normal row indexing; using a deliberately flat allocation avoids cross-subarray pointer-arithmetic subtleties when treating the entire matrix as one buffer.

A `std::vector<T>` supplies ownership and size tracking; `operator[]` still does not perform bounds checking. `.at()` does. Reallocation invalidates existing pointers. Plain `std::vector<float>` does not promise 32-byte or 64-byte alignment.

### 2.4 Array of structures versus structure of arrays

Imagine adding temperature and moisture to each forest cell:

```text
Array of structures (AoS):
[state,temp,moisture] [state,temp,moisture] [state,temp,moisture] ...

Structure of arrays (SoA):
state:     [s0 s1 s2 ...]
temp:      [t0 t1 t2 ...]
moisture:  [m0 m1 m2 ...]
```

SoA gives a loop over temperature contiguous temperature values and avoids loading unused fields. AoS is convenient when each operation needs all fields of one cell. Struct padding also changes the stride; use `sizeof`, not the sum of field sizes, to reason about actual object size.

The existing two-bit `PackedGrid` is another choice entirely: four logical cells share one byte. That saves capacity and traffic, but adds masking/shifting and changes the safe unit of concurrent writes. See section 13.

## 3. Caches, locality and bandwidth

### 3.1 Memory hierarchy

```text
SIMD/scalar registers <--> L1 <--> L2 <--> last-level cache <--> DRAM
     tiny, very close          progressively larger/further away
```

This is a useful model, not a promise that every request literally visits every level in order. Exact topology, latency, bandwidth and inclusion policies depend on the CPU.

A cache operates on **cache lines**, commonly 64 bytes on the x86 machines discussed here. One such line contains:

- 16 floats;
- 8 doubles;
- 8 `std::complex<float>` values;
- 64 one-byte cells;
- 256 two-bit cells, if tightly packed.

Those counts describe capacity, not how many values one instruction processes.

### 3.2 Spatial and temporal locality

**Spatial locality:** use nearby addresses. After accessing `B[k*ld+j]`, consuming `B[k*ld+j+1]` may reuse the same cache line.

**Temporal locality:** reuse the same values before they are evicted. A matrix tile lets many operations reuse a small part of A and B.

A flat array helps spatial locality only when the access order cooperates. A column walk through a row-major matrix is still strided.

For a large matrix with `N=1024` floats per row, walking down one column advances by `1024*4 = 4096` bytes per access. Walking across a row advances by 4 bytes. This large example makes the issue clearer than a `4 × 4` float matrix, which could fit entirely in one 64-byte line.

### 3.3 Loading, storing and eviction

An AVX load requests data for computation. It can be served from cache; it does not necessarily go to DRAM.

A normal cached store updates the memory hierarchy, through store buffers and cache coherence. A modified cache line can remain resident and be reused. **A store does not mean “evict the data” or “write all the way to DRAM immediately.”** Non-temporal/streaming stores have different intended usage and are not the default; using them for an output tile that will immediately be updated again can defeat reuse.

Likewise, cache access is not free. L1 has finite load/store bandwidth and latency, and register spills add traffic even when that traffic hits cache.

### 3.4 Latency, bandwidth and arithmetic intensity

- **Latency:** how long one dependent operation waits for its result.
- **Throughput:** how much work can complete per unit time once operations overlap.
- **Bandwidth:** bytes transferred per unit time.
- **Arithmetic intensity:** arithmetic operations per byte moved at a specified memory level.

If a loop does little arithmetic per byte, making arithmetic faster can leave memory as the limit. If blocking reuses loaded data many times, arithmetic throughput becomes more important.

A rough performance bound is:

```text
achievable FLOP/s <= min(compute peak,
                         memory bandwidth * arithmetic intensity)
```

Use the bandwidth/intensity of the memory level being analysed. This is a model, not a measured speed prediction. Bitwise grid updates also need metrics such as cells/second; FLOP/s is a poor summary of their useful work.

### 3.5 False sharing and actual sharing

**False sharing:** two threads write different memory objects in the same cache line. The values can be logically independent, yet ownership of the line bounces between cores.

```text
one cache line:
[T0's counter][T1's counter][T2's counter][T3's counter]...
```

Prefer local accumulators followed by a reduction; padding frequently written per-thread state can help when measurement supports it. `schedule(static,1)` on adjacent elements can create extensive false sharing.

**Actual race:** two threads modify the same byte while trying to change different packed cells. This is a correctness error, not merely false sharing. Padding cache lines does not make unsynchronised writes to the same byte safe.

### 3.6 A little further: pages, prefetching and NUMA

- The TLB caches virtual-to-physical address translations. Large-stride accesses can increase translation pressure as well as cache misses.
- Hardware prefetchers often recognise sequential streams. Irregular access and pointer chasing are harder to anticipate.
- On NUMA machines, memory attached to another socket can be more expensive to access. Parallel first-touch initialisation can place pages near the threads that will use them, depending on the OS and memory policy.
- Keep thread placement and allocation policy consistent when comparing runs. These details matter after basic correctness, traversal and ownership are sound.

## 4. Matrix multiplication and blocking

### 4.1 What `i`, `j` and `k` mean

For `C = A * B`, with square dimension N:

```text
C[i,j] = sum over k of A[i,k] * B[k,j]

 i -> output row / row of A
 j -> output column / column of B
 k -> reduction dimension joining A's columns with B's rows
```

One output is a dot product. For a three-element row and column:

```text
C[i,j] = a0*b0 + a1*b1 + a2*b2
```

For complex matrix multiplication this remains the formula. Ordinary matrix multiplication does **not** conjugate either operand; a Hermitian inner product is a different operation.

### 4.2 `ijk`: finish one output element

```cpp
for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
        floatType sum = floatType{};
        for (int k = 0; k < N; ++k)
            sum += A[i*N+k] * B[k*N+j];
        C[i*N+j] = sum;
    }
}
```

Indices here are abbreviated for readability; use wide products in real large-matrix code.

Inside `k`: A is contiguous, B strides by N, and the output stays in one accumulator. The local accumulator is good; repeatedly traversing large columns of B can be expensive.

### 4.3 `ikj`: apply one A value across an output row

```cpp
// C must start at zero for C = A*B.
for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j)
        C[i*N+j] = floatType{};
    for (int k = 0; k < N; ++k) {
        const floatType aik = A[i*N+k];
        for (int j = 0; j < N; ++j)
            C[i*N+j] += aik * B[k*N+j];
    }
}
```

For fixed `i,k`, the inner loop reuses `aik` while traversing B and C contiguously:

```text
A row: [a b c]

k=0: C row += a * B row 0
k=1: C row += b * B row 1
k=2: C row += c * B row 2
```

This is friendly to row-wise SIMD: broadcast one A value, load consecutive B values, update consecutive C values.

### 4.4 The six loop orders

For the same row-major expression, focus first on what changes in the innermost loop:

| Order | Inner loop | A access | B access | C access |
|---|---|---|---|---|
| `ijk` | k | Contiguous | Strided | Same output |
| `jik` | k | Contiguous | Strided | Same output |
| `ikj` | j | Same value | Contiguous | Contiguous |
| `kij` | j | Same value | Contiguous | Contiguous |
| `jki` | i | Strided | Same value | Strided |
| `kji` | i | Strided | Same value | Strided |

`ikj` is a strong baseline, not a universally fastest ordering. Outer-loop reuse, compiler choices, datatype and matrix size still matter. `kij` has a similarly good inner loop, but distributing its outer k loop across threads would create competing updates to C.

For the straightforward unblocked forms, `ijk` and `ikj` can both accumulate each C element in increasing k order. Interchanging i/j around k does not by itself require a different per-element summation order. SIMD reductions, split-k algorithms and reassociation can change it.

### 4.5 Blocking: restrict the working set

Blocking changes traversal, not necessarily storage.

With `N=8` and a tile size of 4:

```text
Matrix:             Top-left tile's flat indices:
+-------+-------+     0  1  2  3
| tile00| tile01|     8  9 10 11
+-------+-------+    16 17 18 19
| tile10| tile11|    24 25 26 27
+-------+-------+
```

The tile has contiguous row segments, separated by the full matrix stride. It is not automatically one compact 16-element allocation.

There are two sets of coordinates:

```text
ii, jj, kk -> tile origins
i,  j,  k  -> actual element coordinates within those tiles
```

The outer loops choose a tile. They do not explicitly load it or prepopulate a cache line. Inner accesses trigger the actual loads.

The k tiles accumulate contributions to the same C tile:

```text
C00 = A00*B00 + A01*B10
```

Therefore, **zero the C tile once before its k-tile loop**, not once per k tile.

### 4.6 A safe blocked OpenMP baseline

**Standalone example:** real `double` matrices, separate input/output buffers, compact row-major storage, nonnegative sizes with `n + tile` representable as an int, and positive `tile`. This demonstrates ownership and loop order. It is not the assignment's complex-valued kernel.

```cpp
#include <algorithm>
#include <cstddef>

void matmul_blocked(int n, const double* a, const double* b,
                    double* c, int tile) {
    if (n <= 0 || tile <= 0) return;
    const std::size_t ld = static_cast<std::size_t>(n);

    #pragma omp parallel for collapse(2) schedule(static)
    for (int ii = 0; ii < n; ii += tile) {
        for (int jj = 0; jj < n; jj += tile) {
            const int iend = std::min(ii + tile, n);
            const int jend = std::min(jj + tile, n);

            for (int i = ii; i < iend; ++i)
                for (int j = jj; j < jend; ++j)
                    c[i*ld+j] = 0.0;

            for (int kk = 0; kk < n; kk += tile) {
                const int kend = std::min(kk + tile, n);
                for (int i = ii; i < iend; ++i) {
                    for (int k = kk; k < kend; ++k) {
                        const double aik = a[i*ld+k];
                        #pragma omp simd
                        for (int j = jj; j < jend; ++j)
                            c[i*ld+j] += aik * b[k*ld+j];
                    }
                }
            }
        }
    }
}
```

Why this decomposition is safe:

- One scheduled `(ii,jj)` iteration owns one distinct output tile.
- That owner processes **all** kk contributions to its tile.
- Inner SIMD lanes write different C elements for a fixed i,k.
- A and B are read-only and do not overlap C.
- Edge tiles are bounded with `min`; N need not be divisible by the tile size.

A small tile can increase scheduling overhead or false sharing between neighbouring C tiles. Safety does not imply optimal speed.

**Do not collapse `ii,jj,kk` here.** Different kk iterations contribute to the same output tile. Doing that requires private partial outputs and an explicit combination strategy, not just an extra collapse level.

### 4.7 Choosing a tile and going further

A first capacity estimate for three square tiles of side T is:

```text
working bytes ≈ 3 * T*T * sizeof(element)
```

For doubles or complex floats, a `32 × 32` tile is 8192 bytes; three total 24 KiB. Three `64 × 64` tiles total 96 KiB. These are arithmetic examples, not claims about this machine's cache sizes or an optimal tile.

Leave room for other data, associativity conflicts and multiple threads. A full row-major tile can touch more cache-line bytes than its useful element count, especially for narrow or misaligned row segments.

Further improvements:

- **Hierarchical blocking:** larger blocks for outer cache levels, smaller blocks for L1.
- **Register blocking:** keep a small C microtile in vector accumulators across many k iterations, reducing repeated C loads/stores.
- **Packing:** explicitly copy a tile into a compact layout suited to the microkernel. Unlike ordinary blocking, packing changes the working representation and costs time and space.
- **Transposing B:** makes the `ijk` dot product contiguous in both operands after using `BT[j*ld+k]`. Include the transpose cost; it is not automatically better than `ikj` or packing.

Matrix size affects whether setup costs pay off; hardware, datatype and execution strategy guide tile dimensions. Reusing an input across many multiplies can amortise packing, but the assignment repeatedly changes an accumulated product, so cache validity must be reasoned about carefully.

## 5. SIMD and AVX fundamentals

### 5.1 SIMD is lane-wise work

SIMD means **single instruction, multiple data**. A packed float addition conceptually does:

```text
[ a0 a1 a2 a3 a4 a5 a6 a7 ]
[ b0 b1 b2 b3 b4 b5 b6 b7 ] +
--------------------------------
[ a0+b0 ...               a7+b7 ]
```

This is not addition of one giant 256-bit integer. The instruction defines how the bits are interpreted and where lane boundaries are.

**Vectorisation is different from loop unrolling.** Unrolling duplicates operations to reduce loop overhead and expose independent work; those operations may still be scalar. SIMD uses packed instructions. The compiler can use both.

### 5.2 The types and instruction families

| Type | Bits | Common interpretation |
|---|---:|---|
| `__m128` | 128 | 4 floats |
| `__m256` | 256 | 8 floats |
| `__m256d` | 256 | 4 doubles |
| `__m256i` | 256 | Integer bits, interpreted by each intrinsic: e.g. 32 bytes or 8 int32 lanes |

`__m256 x;` declares a vector value. It does not reserve a physical register. The compiler can keep it in a YMM register, optimise it away, or spill it to memory. Initialising a value is separate from declaring it.

- **AVX:** 256-bit packed floating-point arithmetic and associated loads, stores and rearrangements.
- **AVX2:** extends integer SIMD to 256 bits and adds features including gathers.
- **FMA:** fused multiply-add support; check separately from AVX/AVX2.
- **AVX-512:** a collection of additional extensions, including wider vectors and mask features; do not assume it is available.

Some operations work within each 128-bit half of a 256-bit vector. Check the intrinsic, especially shuffles and horizontal operations. AVX2 has gathers, but no general vector scatter equivalent to AVX-512 scatter.

The [Intel Intrinsics Guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html) identifies instruction-set requirements and operations. Intrinsics can lower to one instruction, several instructions or optimised-away code.

### 5.3 Load, operate, store

```cpp
#include <immintrin.h>

__m256 a = _mm256_loadu_ps(A);    // A[0] ... A[7]
__m256 b = _mm256_loadu_ps(B);
__m256 c = _mm256_add_ps(a, b);
_mm256_storeu_ps(C, c);          // C[0] ... C[7]
```

`_mm256_` indicates a 256-bit intrinsic family; `ps` means packed single-precision floats; `pd` means packed doubles. `u` in these load/store names means unaligned addresses are accepted. It does not mean the source must be unaligned.

An ordinary vector load reads consecutive values. Loading a column of a row-major matrix requires a different approach: change layout/traversal, rearrange loaded data, use several loads, or use supported gather instructions. A gather is not a free replacement for contiguous access.

### 5.4 Tail handling

**Standalone example:** A, B and C have at least n floats; C does not overlap the input buffers. No particular alignment is required.

```cpp
#include <cstddef>
#include <immintrin.h>

void add_avx(const float* a, const float* b, float* c, std::size_t n) {
    std::size_t i = 0;
    for (; n - i >= 8; i += 8) {
        const __m256 av = _mm256_loadu_ps(a + i);
        const __m256 bv = _mm256_loadu_ps(b + i);
        _mm256_storeu_ps(c + i, _mm256_add_ps(av, bv));
    }
    for (; i < n; ++i)
        c[i] = a[i] + b[i];
}
```

For n=19: vector groups cover 0–7 and 8–15; the scalar tail covers 16–18. An unaligned load still reads all eight elements. It does not make reading past the end safe. Do not assume a halo of one cell covers a vector over-read of several cells.

## 6. Alignment, allocation and aliasing

### 6.1 Alignment refers to the starting byte address

32-byte alignment means `address % 32 == 0`.

```text
0x1000: aligned to 32 and 64 bytes
0x1020: aligned to 32, not 64
0x1004: aligned to 4, not 32
```

Allocating eight floats at alignment 64 requests 32 usable bytes with a 64-byte-aligned start. It does not mean 64 floats, and any allocator rounding does not authorise out-of-bounds reads.

### 6.2 Allocation choices

| Method | Ownership/release | Alignment point |
|---|---|---|
| `alignas(32) float a[8];` | Automatic lifetime | Aligns the actual array |
| `_mm_malloc(bytes, 32)` | `_mm_free(pointer)` | Requests aligned raw storage |
| `std::aligned_alloc(32, bytes)` | `std::free(pointer)` | C++17; size must be a multiple of alignment |
| `new T[n]` | `delete[] pointer` | Required alignment of T; plain float does not imply 32-byte alignment |
| `std::vector<T>` | Automatic ownership | Required alignment of T; use an appropriate allocator for extra alignment |

`_mm_malloc` returns a raw pointer, not a container with a length. Initialise elements before reading them and handle allocation failure in real code. For arbitrary C++ class types, raw allocation is also not a substitute for correctly constructing objects. Prefer normal C++ containers for learning unless alignment control is specifically needed.

`alignas(32) float* p;` aligns the **pointer variable**, not the buffer it points to.

The matmul assignment's build uses C++11, so do not copy a C++17 allocation API into it without checking availability and the permitted headers.

### 6.3 Aligned versus unaligned AVX access

| Intrinsic | Floats accessed | Requirement |
|---|---:|---|
| `_mm256_load_ps(p)` | 8 | p is 32-byte aligned |
| `_mm256_loadu_ps(p)` | 8 | No 32-byte alignment requirement |
| `_mm256_store_ps(p,v)` | 8 | p is 32-byte aligned |
| `_mm256_storeu_ps(p,v)` | 8 | No 32-byte alignment requirement |

Using an aligned intrinsic with a misaligned address violates its contract. It may fault or be optimised in a way that makes the bug appear inconsistent. `loadu/storeu` are a sound starting point when alignment is uncertain. The cost difference is hardware/access-pattern dependent, especially across cache lines or pages. See the [official AVX intrinsic definitions](https://clang.llvm.org/doxygen/avxintrin_8h.html).

### 6.4 Base alignment does not imply alignment of every row

For a matrix element address:

```text
address = base + (row*ld + col)*sizeof(T)
```

If base is 64-byte aligned, row starts are 32-byte aligned only if `ld*sizeof(T)` is a multiple of 32.

Examples for compact rows:

- float: N divisible by 8 aligns every row to 32 bytes.
- double: N divisible by 4.
- complex float: N divisible by 4, because each element is 8 bytes.

Starting a tile at a nonaligned column can break alignment even when every row starts aligned. A halo can do the same. Using a padded leading dimension can fix row starts, but an external API's compact `N*N` buffers must still be interpreted with their actual stride. Padding your own scratch buffer does not change the caller's layout.

### 6.5 Pointer reinterpretation is not a load

```cpp
__m256* vectors = reinterpret_cast<__m256*>(floats);
```

This changes the pointer type. It does not pack/copy the elements or perform arithmetic. Conceptually, `vectors+1` advances 32 bytes while `floats+1` advances 4.

Actually reading a vector value still requires the data, whether the generated instruction uses an explicit load or a memory operand. The cast cannot eliminate necessary memory traffic.

Dereferencing such a cast also brings alignment, object-lifetime and type-access rules into play; compiler vector extensions have their own details. Prefer explicit load/store intrinsics to assuming a cast gives portable permission to access any object as a vector.

### 6.6 Aliasing also matters without casts

Two pointers **alias** when accesses through them refer to overlapping storage. `const float* a` means code using that pointer cannot modify through it; it does not prove that some other pointer cannot modify the same data.

If a compiler cannot establish that output writes are independent of later input reads, it may insert overlap checks or avoid vectorisation.

GCC/Clang support `__restrict__` in C++ as an extension for restricted pointer access. It is a contract about aliasing in the relevant scope, not a request to allocate different memory. Do not apply it when the caller can pass overlapping input/output buffers. [GCC restricted-pointer documentation](https://gcc.gnu.org/onlinedocs/gcc/Restricted-Pointers.html).

For matrix multiplication, an output overwriting a still-needed input generally needs a temporary buffer or a documented nonaliasing interface. The PDF's repeated `A = A*B` mathematical description does not, by itself, establish whether the C pointer aliases A in an individual callback.

## 7. Vectorisation patterns and complex numbers

### 7.1 Choose the amount of control you need

| Approach | Use when | Main responsibility |
|---|---|---|
| Compiler auto-vectorisation | A simple independent loop already expresses the work | Check compiler reports and timing |
| `#pragma omp simd` | The compiler needs explicit information about independence/reductions | Ensure the asserted semantics are true |
| AVX intrinsics | You need specific lane layout, shuffles, masks or a microkernel | Manage ISA, alignment, tails and lane arithmetic |

Start with the clearest correct loop. Intrinsics are useful when you can explain what they improve; more intrinsics do not automatically mean a faster program.

### 7.2 Broadcast and row updates

`_mm256_set1_ps(x)` constructs `[x x x x x x x x]`. For real-float `ikj` matmul:

```cpp
// Inside one i,k pair; at least 8 columns remain from j.
__m256 av = _mm256_set1_ps(A[i*ld+k]);
__m256 bv = _mm256_loadu_ps(B + k*ld+j);
__m256 cv = _mm256_loadu_ps(C + i*ld+j);
cv = _mm256_add_ps(cv, _mm256_mul_ps(av, bv));
_mm256_storeu_ps(C + i*ld+j, cv);
```

Use this pattern for “one coefficient times a contiguous row.” This example is **real float only**. For the assignment's complex coefficients, use the arithmetic in section 7.6.

### 7.3 Fused multiply-add

```cpp
cv = _mm256_fmadd_ps(av, bv, cv);  // av*bv + cv, per float lane
```

FMA fuses multiplication and addition with one final rounding. It can therefore produce a slightly different result from separately rounded multiply then add. An eight-float FMA represents 16 conventional real floating-point operations.

FMA is not inherently an expensive choice compared with separate multiply and add. Latency and throughput are different: a dependency chain through one accumulator can stall while several independent accumulators can overlap execution. The useful choice depends on the CPU and generated loop. [Official FMA intrinsic definitions](https://clang.llvm.org/doxygen/fmaintrin_8h.html).

The supplied matmul build enables `-mavx`; it does **not** explicitly enable `-mfma` or `-mavx2`. Check the actual grading target/flags before using those extensions. FMA is also not a natural substitute for Boolean state transitions in the packed forest grid.

### 7.4 Reductions across lanes

Adding two vectors lane-wise does not sum all lanes into one scalar.

For a dot product, accumulate several products per lane, then combine lanes at the end. This avoids a scalar dependency for every element. `omp simd reduction(+:sum)` can express that without manual shuffles.

Be careful with names such as `_mm256_hadd_ps`: a horizontal operation need not combine the entire 256-bit register into one value. Many operations treat the two 128-bit halves separately. Check the exact lane diagram before using it.

Use a reduction when many iterations contribute to a common mathematical result. Use independent vector outputs when each lane has its own result, such as different j values in an `ikj` row update.

### 7.5 Masks, comparisons and branchless selection

SIMD comparisons produce masks that identify which lanes satisfy a condition. Bitwise operations or blends then select the result per lane:

```text
condition: [true false true false ...]
yes:       [  A     B    C     D ...]
no:        [  W     X    Y     Z ...]
selected:  [  A     X    C     Z ...]
```

Use this when a branchy elementwise rule becomes awkward to vectorise. It is especially relevant to forest cells having different states in the same vector.

Important details:

- Many x86 comparison masks use all-one bits for true, not integer 1 or floating-point 1.0.
- `&&` / `||` short-circuit in scalar C++; `&` / `|` do not. Replacing one with the other can change what gets evaluated.
- Selection after evaluating both sides does not make an invalid load or division safe. Avoid the invalid operation itself or use an instruction with the required masking semantics.
- A perfectly predictable branch can be cheaper than calculating both alternatives.
- A PCG result is unsigned 32-bit. A signed SIMD comparison is not directly equivalent to `uint32_t r < threshold`. An AVX2 technique is to flip the sign bit of both operands before a signed comparison; the datatype and ISA must be checked.
- Packed cells need per-cell masks and shifts. An arbitrary nonzero byte does not mean all four cells are burning.

A one-cell halo can still be useful with SIMD: it defines boundary values and simplifies neighbour access. Removing it is not an automatic optimisation.

### 7.6 The assignment uses complex floats

The supplied `include/rubric.h` defines `FLOATTYPE_COMPLEX64`, making `floatType` equal to `std::complex<float>`.

```text
one complex value = real float + imaginary float = 8 bytes
one __m256        = 8 float lanes = 4 complex values

lane:  0   1   2   3   4   5   6   7
       r0  i0  r1  i1  r2  i2  r3  i3
```

The standard complex floating-point specialisations allow access to arrays as interleaved real/imaginary scalar components. This is a specific guarantee for `std::complex`, not permission to reinterpret arbitrary structs as float arrays. [C++ complex layout requirements](https://eel.is/c++draft/complex.numbers).

Complex multiplication needs cross terms:

```text
(ar + i*ai) * (br + i*bi)
    real = ar*br - ai*bi
    imag = ar*bi + ai*br
```

Simply calling `_mm256_mul_ps` on two interleaved complex arrays computes `[ar*br, ai*bi, ...]`, which is not complex multiplication.

For one complex A coefficient times four consecutive B values:

```text
broadcast ar:       [ar ar ar ar ar ar ar ar]
broadcast ai:       [ai ai ai ai ai ai ai ai]
B:                 [br0 bi0 br1 bi1 br2 bi2 br3 bi3]
B with pairs swapped:
                   [bi0 br0 bi1 br1 bi2 br2 bi3 br3]

product = alternating subtract/add of (ar*B) and (ai*swapped_B)
```

**Standalone example:** an AVX-only complex row update, `c[j] += a*b[j]`, for nonoverlapping b/c buffers of length n. Intended for finite values whose intermediate arithmetic remains finite. Exceptional NaN/infinity/overflow handling need not match every detail of `std::complex` library arithmetic.

```cpp
#include <complex>
#include <immintrin.h>

void complex_row_update_avx(std::complex<float> a,
                            const std::complex<float>* b,
                            std::complex<float>* c, int n) {
    if (n <= 0) return;
    const __m256 ar = _mm256_set1_ps(a.real());
    const __m256 ai = _mm256_set1_ps(a.imag());
    int j = 0;
    for (; n - j >= 4; j += 4) {
        const float* bp = reinterpret_cast<const float*>(b + j);
        float* cp = reinterpret_cast<float*>(c + j);
        const __m256 bv = _mm256_loadu_ps(bp);
        const __m256 swapped = _mm256_permute_ps(bv, 0xB1);
        const __m256 product = _mm256_addsub_ps(
            _mm256_mul_ps(ar, bv), _mm256_mul_ps(ai, swapped));
        const __m256 cv = _mm256_loadu_ps(cp);
        _mm256_storeu_ps(cp, _mm256_add_ps(cv, product));
    }
    for (; j < n; ++j)
        c[j] += a * b[j];
}
```

`0xB1` swaps neighbouring float lanes within each 128-bit half. `_mm256_addsub_ps` subtracts in even-numbered lanes and adds in odd-numbered lanes, producing the real/imaginary pairs above. The loop advances by **four complex elements**, not eight.

Use this as a building block to understand complex `ikj` vectorisation. A high-performance microkernel might keep C vectors in registers across multiple k iterations. Complex arithmetic makes shuffles directly relevant to this assignment, despite the earlier note suggesting they might be unnecessary.

## 8. OpenMP teams and work distribution

### 8.1 `parallel`: every team member runs the block

```cpp
#include <cstdio>
#include <omp.h>

#pragma omp parallel num_threads(4)
{
    std::printf("thread %d of %d\n",
                omp_get_thread_num(), omp_get_num_threads());
}
```

The pragma establishes a team; `printf` does not spawn threads. Every member executes the block. Thread 0 is the primary thread of that team, and the team size includes it. A team of eight means eight participants total, not eight extra workers plus the original thread.

The runtime may reuse worker threads across regions rather than create new OS threads every time. Region entry/exit and synchronization still have costs. Requested team sizes can be constrained by runtime settings and available resources. Printing order is unspecified. [OpenMP parallel semantics](https://www.openmp.org/spec-html/5.2/openmpse57.html).

Use `parallel` when a group of operations should share one team, especially repeated simulation steps.

### 8.2 `for`: distribute iterations across an existing team

```cpp
#pragma omp parallel
{
    #pragma omp for
    for (int i = 0; i < N; ++i)
        output[i] = calculate(i);
}
```

Without `omp for`, a plain loop inside `parallel` is executed in full by every thread. With it, the iterations are divided among the team. `omp for` itself does not create a new team.

The combined form is convenient for a single loop:

```cpp
#pragma omp parallel for schedule(static)
for (int i = 0; i < N; ++i)
    output[i] = calculate(i);
```

Use it when each iteration's writes are independent of other iterations, or when a supported reduction expresses the shared result. Read-only shared inputs are fine.

### 8.3 Thread controls worth knowing

| Control | Meaning |
|---|---|
| `OMP_NUM_THREADS=4` | Requests team size through the runtime environment |
| `num_threads(4)` | Requests a size for a particular parallel region |
| `omp_set_num_threads(4)` | Sets the relevant runtime default for subsequent regions |
| `omp_get_thread_num()` | Calling thread's ID within its current team |
| `omp_get_num_threads()` | Actual team size; normally 1 outside a parallel region |
| `omp_get_max_threads()` | A bound/default relevant to a subsequent region, not the current team count |
| `OMP_DYNAMIC=FALSE` | Disables dynamic team-size adjustment; unrelated to loop `schedule(dynamic)` |
| `OMP_PLACES=cores` | Describes placement locations based on cores |
| `OMP_PROC_BIND=close` / `spread` | Placement policies worth measuring for the target machine |

Do not use `std::thread::hardware_concurrency()` as the authority for a Slurm allocation. It is a hardware hint, not the number of cores your job was granted. Avoid nested teams or internally threaded libraries accidentally oversubscribing the allocation.

### 8.4 Scheduling: how iterations are assigned

| Schedule | What happens | When to try it |
|---|---|---|
| `static` | Iterations are divided into approximately equal chunks with low scheduling overhead | Regular matrix tiles, uniform row work |
| `static,chunk` | Fixed-size chunks are assigned cyclically | Controlled chunking; watch locality |
| `dynamic,chunk` | Workers request another chunk after finishing | Substantial unpredictable imbalance |
| `guided,chunk` | Dynamically assigned chunks generally shrink toward a minimum | Irregular work with less overhead than tiny dynamic chunks |
| `runtime` | Reads schedule choice from `OMP_SCHEDULE` | Compare policies without recompiling |
| `auto` | Compiler/runtime chooses | Implementation-dependent experimentation |

With N=16 and four workers, `static,1` distributes alternating elements to workers; `static,4` distributes groups of four. Plain `static` is usually a good first experiment, but do not rely on a particular remainder-partition formula unless you implement that partition yourself.

For dense matmul, work per tile is regular except edges. For a forest grid, branches differ by cell state, but that alone does not establish that dynamic scheduling will pay for its overhead. Large contiguous chunks preserve locality and make storage ownership easier to reason about.

Reference for scheduling details: [OpenMP worksharing loops and schedules](https://www.openmp.org/spec-html/5.1/openmpsu48.html).

### 8.5 `collapse`: expose more logical iterations

```cpp
#pragma omp parallel for collapse(2) schedule(static)
for (int row = 0; row < rows; ++row)
    for (int col = 0; col < cols; ++col)
        out[row*cols+col] = calculate(row, col);
```

For four rows and ten columns, OpenMP sees 40 `(row,col)` iterations instead of only four outer iterations. Conceptually, for these rectangular loops:

```text
q = row*cols + col
row = q / cols
col = q % cols
```

This does not physically flatten or rearrange storage. The compiler need not literally perform division for every iteration.

Use collapse when the outer loop offers too little work, for instance two rows but many columns and many threads. It is not automatically useful when there are already thousands of rows.

Use simple canonical, directly nested loops as the portable starting point. Support for nonrectangular or imperfect nests varies by OpenMP version/compiler. More importantly, **the newly distributed iterations must be safe to run concurrently**. [OpenMP collapse clause](https://www.openmp.org/spec-html/5.2/openmpsu30.html).

Examples:

- Collapse `(i,j)` in an `ijk` algorithm where each pair writes its own C element: reasonable.
- Collapse `(ii,jj)` when each pair owns a full C tile across all kk: reasonable.
- Collapse `(i,k)` in `ikj`: races on C unless redesigned.
- Collapse `(i,j,k)` in direct `C[i,j] += ...`: races on C.
- Collapse forest cells calling the existing packed `set()`: not safe merely because cell indices differ.

## 9. Who owns each variable?

### 9.1 Data-sharing clauses

| Clause / declaration | Initial state | Result after the construct | Use when |
|---|---|---|---|
| `shared(x)` | Same original object | Changes affect that object | Read-only inputs or safely partitioned outputs |
| `private(x)` | Separate copy; fundamental types are uninitialised | Original unchanged | Scratch state initialised before use |
| `firstprivate(x)` | Separate copy initialised from original | Original unchanged | Each worker/task needs the same starting value |
| `lastprivate(x)` | Private state; no implicit copy-in | Copies value from logically last iteration | Need the sequentially last loop result |
| `reduction(+:x)` | Private accumulators start at additive identity | Combines with original x | Sum/count/dot-product accumulation |
| Local automatic variable inside `parallel` | Each thread executes its own declaration | Normal local lifetime | Simple per-thread scratch/RNG objects |
| C++ `thread_local` | One instance per underlying thread | Persists for that thread's lifetime | State deliberately reused across calls/regions |

Initialise fundamental private variables before reading them. C++ class objects follow construction rules; `private` does not simply copy the original class object's value.

`firstprivate` and `lastprivate` are copy-in/copy-out tools, not synchronization primitives. [Firstprivate](https://www.openmp.org/spec-html/5.2/openmpsu38.html), [lastprivate](https://www.openmp.org/spec-html/5.2/openmpsu39.html).

### 9.2 Prefer obvious local scratch and explicit sharing

```cpp
#pragma omp parallel default(none) shared(a, out, N)
{
    double local_scratch = 0.0;
    #pragma omp for
    for (int i = 0; i < N; ++i) {
        local_scratch = 2.0 * a[i];
        out[i] = local_scratch;
    }
}
```

Each thread has its own `local_scratch`. The loop index is private according to the loop's rules. The arrays are shared, but each output element has one writer. `default(none)` helps surface accidental sharing by requiring explicit attributes where no predetermined rule applies.

There is no rule that every shared array write requires an atomic. The important question is whether concurrent accesses conflict on the same memory location.

### 9.3 A private pointer is not a private allocation

```cpp
float* p = buffer;
#pragma omp parallel firstprivate(p)
{
    // Each thread has a copy of the address.
    // All copies still point into the same buffer.
}
```

`private(p)` would instead leave the private pointer uninitialised; it would not allocate a new array. To get independent storage, actually allocate/declare separate buffers or give each worker a disjoint range of one buffer.

The same warning applies to firstprivate objects holding pointers: a shallow pointer copy does not copy the pointed-to data.

### 9.4 `lastprivate` means logical order

```cpp
int last = -1;
#pragma omp parallel for lastprivate(last)
for (int i = 0; i < 100; ++i)
    last = 2 * i;
// last == 198
```

This copies from iteration i=99, even if that iteration finishes before another worker. It does not mean “the last worker to finish wins.” If the loop is empty or the logically last iteration does not assign a valid value, do not assume this pattern produces a useful result.

### 9.5 `thread_local`, OpenMP private and RNG state

C++ `thread_local` is independent of OpenMP. It is initialised on first use by each thread and persists for that thread's lifetime. OpenMP `threadprivate` is a separate directive with its own rules, including conditions on persistence across regions.

A simple reproducible-start approach is a region-local generator:

```cpp
#pragma omp parallel
{
    const int tid = omp_get_thread_num();
    pcg32 local_rng(master_seed, static_cast<std::uint64_t>(tid) + 1);
    // This thread advances its own generator while doing its assigned work.
}
```

This sketch uses the project's PCG constructor with state seed and stream selector. Distinct streams avoid starting every worker at the exact same sequence, but do not promise reproduction of the old serial sequence or invariance across schedules/thread counts.

Use a persistent parallel region to keep each local RNG alive over timesteps. If instead using `thread_local`, a later simulation call with a different master seed will not automatically reinitialise an already-existing generator. Decide explicitly when it resets.

## 10. Synchronization and reductions

### 10.1 Why `sum += value` races

It is logically read → add → write:

```text
sum starts at 100
T0 reads 100            T1 reads 100
T0 adds 5               T1 adds 7
T0 writes 105           T1 writes 107

Expected 112; one update was lost.
```

Declaring sum `shared` exposes the same object to everyone; it does not protect updates. Hardware cache coherence also does not turn the compound operation into a race-free update.

Initialise shared state before entering the region, or once in a properly synchronised `single`. Having all workers execute `sum = 0` inside a parallel region is a race even if all write the same value. A late reset can erase another worker's updates.

### 10.2 Atomic operations

| Construct | Meaning | Example use |
|---|---|---|
| `atomic update` | Indivisible supported read-modify-write | Increment a shared counter |
| `atomic read` | Atomic read of the designated location | Read a concurrently updated scalar |
| `atomic write` | Atomic write to the designated location | Publish a scalar value |
| `atomic capture` | Update plus capture related old/new value | Allocate a unique ticket |
| `atomic compare` | Supported conditional update | Compare-and-update; newer compiler support needed |

```cpp
#pragma omp atomic update
count += contribution;

#pragma omp atomic read
snapshot = count;              // snapshot is private

#pragma omp atomic write
count = new_value;

#pragma omp atomic capture
{
    ticket = next_ticket;      // ticket is private
    next_ticket++;
}
```

Plain `atomic` defaults to update. Capture's brace syntax does not permit arbitrary protected code. Concurrent accesses to the same object need a consistent synchronization design; atomic updates do not protect simultaneous plain accesses. [OpenMP atomic forms](https://www.openmp.org/spec-html/5.1/openmpsu105.html).

Use atomics for occasional shared scalar operations. An atomic per cell or per multiply-add often creates a serialization bottleneck. An atomic also does not protect the calculation of an arbitrary right-hand side or an entire called function.

### 10.3 Atomicity versus memory ordering

Making a flag atomic and ensuring that it publishes other data are different concerns. Acquire/release ordering can establish that relationship; a barrier often expresses a phase boundary more simply.

Do not assume a plain OpenMP atomic has the same default memory-order semantics as default C++ `std::atomic` operations. OpenMP 5.1 specifies relaxed ordering when no applicable explicit/default order is provided. Avoid inventing a producer/consumer spin loop from an atomic flag without an ordering design. [OpenMP memory-order examples](https://www.openmp.org/wp-content/uploads/openmp-examples-5.1.pdf).

`volatile` is not a threading solution. An OpenMP `flush` is a memory-model operation, not a command to empty the CPU cache, and does not make racy operations atomic.

### 10.4 `critical`: one participant at a time

```cpp
#pragma omp critical(stats_lock)
{
    total += value;
    samples.push_back(value);
}
```

Use this for a short compound operation that must preserve an invariant, or a shared container whose update cannot be represented by a supported atomic operation.

Every access that needs the protected invariant must use the same synchronization discipline. A reader outside the lock does not magically see a consistent pair of updates.

- Same critical name: mutually excludes the other occurrences with that name.
- Different names: distinct exclusion domains.
- Unnamed critical regions: share one unnamed exclusion domain.
- A critical region does not wait for all workers to reach a phase boundary.

Do not put the whole heavy computation inside the critical block. For queue work, remove a job while holding the lock and process it afterwards if the job is independently owned. Explicit `omp_lock_t` / `omp_set_lock` / `omp_unset_lock` are useful when lock lifetime/control needs to be managed directly.

### 10.5 `barrier`: wait for the team

```cpp
#pragma omp parallel
{
    produce_my_part();
    #pragma omp barrier
    consume_complete_result();
}
```

Use a barrier when the next phase requires everyone to finish the previous phase. It also establishes the required visibility/order for that shared data. It does not prevent races that already occurred within the preceding phase.

All participating team threads must encounter the relevant barriers in a consistent sequence. Putting a barrier only inside `if (tid == 0)` is invalid and can hang.

Common implicit barriers:

| Construct | Barrier at end? |
|---|---|
| `parallel` | Yes |
| `for` | Yes, unless `nowait` |
| `single` | Yes, unless `nowait` |
| `sections` | Yes, unless `nowait` |
| `master` / plain `masked` | No |
| `critical` / `atomic` | No team barrier |

A `single` has no implicit barrier **on entry**. If its work needs all earlier writes complete, there must already be a barrier or an equivalent dependency before it.

### 10.6 `nowait`: remove an unnecessary barrier

```cpp
#pragma omp parallel
{
    #pragma omp for nowait
    for (int i = 0; i < N; ++i)
        a[i] = make_a(i);

    #pragma omp for
    for (int i = 0; i < N; ++i)
        b[i] = make_b(i);      // independent of a
}
```

Use this only after establishing that the next work does not consume unfinished results. The example assumes disjoint a/b buffers and independent functions. For forest-fire neighbour reads, each timestep needs the completed previous grid; removing that dependency's barrier is unsafe.

### 10.7 Reduction: local accumulation, then combine

```cpp
long long count = 0;
#pragma omp parallel for reduction(+:count)
for (int i = 1; i <= 40000; ++i)
    count += i;
// count == 800020000
```

OpenMP creates private accumulators and combines them with the original count. For `+`, private copies start at zero. If the original count starts at 10, the result includes that original 10 once, not once per thread.

```text
T0: private subtotal --+
T1: private subtotal --+--> combine --> original result
T2: private subtotal --+
T3: private subtotal --+
```

Use reductions for sums, counts, norms, minima and maxima. Common forms include `reduction(+:sum)`, `reduction(*:product)`, `reduction(max:largest)` and `reduction(min:smallest)`. Choose a valid initial original value, such as an appropriate lowest value for a maximum that may contain negatives. [Reduction semantics](https://www.openmp.org/spec-html/5.2/openmpsu52.html).

A manual equivalent for addition is one local subtotal per thread, followed by **one** atomic addition per thread. Reduction normally expresses that intent more clearly.

Floating-point addition is not associative. Different reduction groupings can change rounding. A reduction with `nowait` still needs synchronization before other workers use the combined original result.

## 11. Single, master, sections and tasks

### 11.1 `single`, `master` and `masked`

| Construct | Who executes? | Use when |
|---|---|---|
| `single` | One selected team member | Swap buffers or perform one team-wide housekeeping action |
| `single nowait` | One selected member; others continue | Work may safely overlap subsequent work |
| `master` | Team primary thread, ID 0 | Code specifically requires the primary thread |
| `masked` without filter | Team primary thread | Modern generalisation of master, if supported |

`master` and `masked` have no implicit barrier. Newer `masked filter(...)` forms can select participating threads; don't treat every masked form as automatically “one arbitrary thread.” Check compiler support before replacing teaching examples using master.

```cpp
#pragma omp single
{
    std::swap(current, next);
}
// The single's end barrier makes the completed swap visible before proceeding.
```

A preceding worksharing-loop barrier is still needed if the swap consumes everyone else's output. [OpenMP single semantics](https://www.openmp.org/spec-html/5.2/openmpse62.html).

### 11.2 `sections`: a few different independent jobs

```cpp
#pragma omp parallel sections
{
    #pragma omp section
    analyse_dataset_a();

    #pragma omp section
    analyse_dataset_b();
}
```

Each section runs once. With two sections, at most two execute concurrently regardless of team size; one worker can execute more than one section. There is normally a barrier at the end.

Use this for a small fixed number of independent jobs. A report that reads unfinished analysis output cannot simply be put in a concurrent section with the analysis.

### 11.3 Tasks: work scheduled onto workers

```cpp
#pragma omp parallel
{
    #pragma omp single
    {
        #pragma omp task
        do_job_a();

        #pragma omp task
        do_job_b();

        #pragma omp taskwait
        use_both_results();
    }
}
```

The single thread generates the tasks once. Any eligible worker may execute a task, potentially immediately. Without the `single` (or another deliberate generating scheme), every thread could generate duplicate tasks.

Use tasks for irregular, recursive or dependency-driven work. A regular dense matrix/grid loop is often simpler with `for`.

- Plain `taskwait` waits for the encountering task's previously generated direct child tasks; it is not a team barrier.
- A `taskgroup` can express waiting for a group's tasks and their relevant descendants.
- `depend(in:...)`, `depend(out:...)` and `depend(inout:...)` describe ordering through matching storage locations between applicable tasks, typically siblings generated by the same parent. They do not copy data or provide general locks for unrelated accesses.
- Captured values and shared buffers must remain alive until the tasks finish. `firstprivate(i)` is useful for passing a loop's current index into a task.
- Thread-local state belongs to the executing thread, not to a logical task. Do not assume a task owns an RNG merely because the RNG is thread-local.

### 11.4 Relation to Go and IPC

OpenMP host threads share a process address space. They normally exchange results by reading/writing shared data with appropriate synchronization. OpenMP does not provide a built-in typed channel with Go's send/receive semantics.

| Familiar Go idea | Nearest useful OpenMP analogy | Limit of the analogy |
|---|---|---|
| Goroutine | Task | Scheduling, suspension and I/O behaviour differ |
| OS worker thread | OpenMP worker | A worker executes work; it is not a lightweight task |
| Mutex | Critical region / explicit lock | Critical naming and scope rules matter |
| WaitGroup-like waiting | Taskwait / taskgroup / barrier | Each waits for a different set of work |
| Channel | No direct construct | Dependencies describe ordering, not message transfer |

A channel-like queue can be built with locks/atomics, but introduces an additional concurrency design. MPI is the separate process/message-passing topic reserved for later.

## 12. OpenMP SIMD

### 12.1 `simd` versus `parallel for simd`

```cpp
// SIMD within the encountering thread; no new thread team.
#pragma omp simd
for (int i = 0; i < N; ++i)
    c[i] = a[i] + b[i];
```

```cpp
// Threads distribute the loop; SIMD works within their chunks.
#pragma omp parallel for simd schedule(static)
for (int i = 0; i < N; ++i)
    c[i] = a[i] + b[i];
```

Use the first for a vectorisable loop already owned by one worker, such as the j loop of a matrix tile. Use the second for a large independent loop worth distributing across cores too.

`omp simd` states execution semantics the compiler may exploit; it is not merely a harmless performance hint. You remain responsible for dependencies. Generated vector width and instructions are implementation-dependent, so inspect the output/report. [OpenMP SIMD semantics](https://www.openmp.org/spec-html/5.2/openmpse60.html).

### 12.2 SIMD reduction

```cpp
double sum = 0.0;
#pragma omp parallel for simd reduction(+:sum)
for (int i = 0; i < N; ++i)
    sum += a[i] * b[i];
```

This combines thread-level and lane-level accumulation. The final grouping can differ from the serial loop; use an appropriate numerical comparison.

For one scalar sum inside a single thread, use `#pragma omp simd reduction(+:sum)`. Do not try to fix a dependency by declaring sum private without combining the private values.

### 12.3 Useful SIMD clauses

| Clause / directive | Meaning | When to use it |
|---|---|---|
| `aligned(a,b:32)` | Promise that the named target addresses satisfy alignment | You control and have verified allocation and offsets |
| `simdlen(8)` | Preferred number of concurrent logical iterations | Experiment with a justified width |
| `safelen(8)` | Bounds the permitted distance between iterations executing in one SIMD chunk | A precisely understood loop-carried dependency permits limited concurrency |
| `linear(p:1)` | Describes a value advancing by a fixed step per logical iteration | An induction variable needs an explicit linear relationship |
| `reduction(+:sum)` | Private lane accumulation plus combination | Dot products, sums, counts |
| `collapse(n)` | Associates multiple loops with the SIMD construct | The combined iteration space has valid dependencies/layout |
| `declare simd` | Enables vector variants of a function where supported | Function calls obstruct vectorisation and the function meets the rules |
| `nontemporal(...)` | Indicates low expected temporal reuse | Streaming data after measurement; not a forced cache eviction |

The `aligned` clause does not allocate, align or repair a buffer. [Aligned clause](https://www.openmp.org/spec-html/5.2/openmpse33.html).

`simdlen(8)` counts logical iterations, not necessarily floats or registers. With complex elements, eight iterations may require several vector registers. If both simdlen and safelen are specified, simdlen must not exceed safelen.

For a dependency at distance eight, such as `a[i] = a[i-8] + 1`, `safelen(8)` can describe why concurrently processed iterations must not be separated by eight or more within a SIMD chunk. It is not a general tool for removing arbitrary dependencies; use it only after proving the dependence distance and checking compiler support.

```cpp
#pragma omp declare simd
float square_plus_two(float x) {
    return x*x + 2.0f;
}
```

Inlining may already make such a function vectorisable. A stateful scalar RNG call does not become a correct SIMD RNG merely by adding `declare simd`.

## 13. Applying this to the forest-fire simulation

### 13.1 What the current implementation actually does

Checked in the current source, not inferred from the old conversations:

- `CellState` is an enum with underlying `uint8_t`: Empty=0, Tree=1, Burning=2.
- `PackedGrid` stores **two bits per cell**, four cells per byte.
- `main.cpp` adds a one-cell border on each side: physical width `W = requested_size + 2`.
- Flat indexing is `x*W+y`; y is the contiguous inner coordinate in this implementation.
- Neighbours are `index-1`, `index+1`, `index-W`, `index+W`. Coordinate names do not alter those physical strides.
- Current and next grids are separate; they are swapped after a complete update.
- One `pcg32 rng(80085)` draws **one value per interior cell per timestep**, before the state switch, including for burning cells.
- The current loop is serial. The Makefile does not enable OpenMP by default.
- The debug reference check depends on the final state and therefore on the exact random stream, draw order and update rules.

Relevant files: `main.cpp`, `packed_grid.hpp`, `packed_grid.cpp`, `pcg32.h`, `hash_grid.cpp` and `Makefile` in this repository. The older discussion about a shared `mt19937` transfers conceptually to shared mutable PCG state; it is not the current RNG type.

### 13.2 Double buffering defines a synchronous update

```text
read current grid at time t
             |
compute each cell's next state using only time-t neighbours
             |
write next grid at time t+1
             |
wait for all output writes
             |
swap current and next once
             |
make the swap visible before starting the next timestep
```

Use this when all cells must update from the same old state. Updating in place allows some cells to observe new neighbours and others old neighbours, changing the simulation even in serial execution.

Concurrent reads of the current buffer are fine. Concurrent writes require independent **storage locations**, which is the difficulty with the packed representation.

### 13.3 Two-bit packing changes the ownership unit

The existing accessors compute:

```cpp
byte_index = index >> 2;       // index / 4
shift      = (index & 3u) << 1; // 2 * (index % 4)
state      = (data[byte_index] >> shift) & 3u;
```

A set operation reads the byte, clears two bits, inserts the new state and writes the byte back:

```text
byte = (old_byte & ~cell_mask) | encoded_state
```

Two different logical cells can share that byte:

```text
one byte: [cell3:2 bits][cell2:2 bits][cell1:2 bits][cell0:2 bits]
```

T0 updating cell0 and T1 updating cell1 can both read the same old byte and then overwrite each other's changes. Neither `collapse(2)` nor `omp simd` fixes this.

**Use one of these ownership designs before parallelising writes:**

1. **Whole-byte or whole-word output ownership.** One worker computes all cells represented by its owned storage unit and writes that unit. Handle border and tail cells explicitly. This needs an appropriate packed-storage operation; the current API does not expose one.
2. **Separate scratch output per worker, then combine.** Easier to make independent, but costs storage and merging.
3. **A byte-per-cell compute buffer.** Easier scalar/SIMD access and ownership; pack only for storage if useful. Measure its extra traffic against the saved bit operations.

Assigning complete rows is not a universal fix. Packed rows need not start on byte boundaries, and chunk boundaries must be checked against the actual written bytes. Cache-line alignment is an additional performance consideration after byte ownership is correct.

For a physical `W*W` grid, the two current packed buffers require approximately `2*ceil(W*W/4)` bytes for cell data, excluding vector/container overhead. Two byte-per-cell buffers require `2*W*W` bytes. Four times less capacity does not guarantee four times higher throughput.

### 13.4 A simple byte-grid teaching example

**Standalone example, not a patch to `PackedGrid`:** one synchronous update using independent byte outputs and precomputed random values. Both grid buffers have `(n+2)*(n+2)` bytes, with valid zero halos. `random_values` contains n*n values in row-major interior order. All three buffers are separate. Thresholds use the caller's existing probability convention.

```cpp
#include <cstddef>
#include <cstdint>

void forest_step_bytes(const std::uint8_t* current,
                       std::uint8_t* next,
                       const std::uint32_t* random_values,
                       int n, std::uint32_t p_threshold,
                       std::uint32_t f_threshold) {
    if (n <= 0) return;
    const std::size_t width = static_cast<std::size_t>(n) + 2;
    #pragma omp parallel for schedule(static)
    for (int row = 1; row <= n; ++row) {
        #pragma omp simd
        for (int col = 1; col <= n; ++col) {
            const std::size_t index = row*width + col;
            const std::size_t q = static_cast<std::size_t>(row-1)*n + col-1;
            const std::uint32_t r = random_values[q];
            const std::uint8_t state = current[index];
            const bool near_fire =
                current[index-1] == 2 || current[index+1] == 2 ||
                current[index-width] == 2 || current[index+width] == 2;
            std::uint8_t result = 0;
            if (state == 0)
                result = (r < p_threshold) ? 1 : 0;
            else if (state == 1)
                result = (near_fire || r < f_threshold) ? 2 : 1;
            next[index] = result;
        }
    }
}
```

Use this as a clear model of parallel cell ownership. It preserves the supplied r-per-cell interpretation, but precomputing randomness adds work and a 4-byte value per interior cell. It might overwhelm the memory savings of packing. No performance advantage is claimed.

The neighbour tests above are valid because all interior cells have a halo. They are written as Boolean expressions; the compiler decides whether/how to use masks. Keeping a pragma does not prove that vector code was generated.

### 13.5 RNG choices and reproducibility

| RNG strategy | Concurrent state ownership | Reproducibility implications |
|---|---|---|
| One unsynchronised shared generator | Unsafe | Data race |
| One locked generator | Safe generator access, serialised | Which cell receives each draw can still depend on scheduling |
| Per-thread generators | Each worker owns its state | Fixed seeds alone do not ensure thread-count/schedule invariance |
| Precompute a serial random array | Parallel update only reads it | Can preserve old draw-to-cell mapping; costs memory and generation time |
| Counter-based or cell-indexed generation | No mutable shared generator needed | Can map `(seed,timestep,cell)` deterministically; changes the old algorithm unless deliberately matched |
| Correct skip-ahead into the old stream | Private copies advance to assigned positions | Can preserve the serial stream if positions and advancement are exact |

The current `pcg32.h` includes `advance(...)`, which makes skip-ahead an option to investigate.

Let `G` be the requested interior width and `M=G*G`. For current loop coordinates x,y starting at 1, the zero-based serial draw position is:

```text
q        = (x-1)*G + (y-1)
position = timestep*M + q
```

Starting from a freshly seeded copy of the baseline generator, advancing by `position` and then calling `nextUInt()` should produce the same draw as the serial loop at that position. This relies on exactly one draw per interior cell and no other generator calls. Use wide arithmetic and respect the advance API's range.

Copying and advancing separately for every cell is usually an unattractive implementation. A more practical scheme assigns a contiguous range of **logical draw positions** to each worker and advances once to its starting position. Packed-byte ownership and interior-only draw ordering must both be satisfied; a contiguous physical range can contain halo positions that consume no draws.

Changing RNG family, streams, draw count or draw-to-cell mapping can change the existing final hash. That is not automatically a parallel race, but it means exact equivalence with the serial reference has not been preserved. Decide whether the experiment requires bit-for-bit reproduction or statistical equivalence, and report which was checked.

### 13.6 Keep a team alive across timesteps

**Structural pseudocode:** assumes safe disjoint output ownership and a correctly designed deterministic random-value provider. `update_owned_storage` is a design placeholder, not an existing repository function.

```cpp
#pragma omp parallel
{
    // Per-thread scratch/RNG initialisation, if the chosen design needs it.
    for (int t = 0; t < timesteps; ++t) {
        #pragma omp for schedule(static)
        for (int unit = 0; unit < output_units; ++unit)
            update_owned_storage(current, next, unit, t);
        // Implicit for barrier: the next grid is complete.

        #pragma omp single
        {
            std::swap(current, next);
            // Optional serial frame output belongs here if enabled.
        }
        // Implicit single barrier: all threads see the completed swap.
    }
}
```

Use this to avoid repeatedly entering/leaving a team for a small timestep. The local t counter progresses through the same synchronized phases on each thread. Do not put another `parallel for` inside this region unless nested parallelism is deliberate; use `omp for` with the existing team.

### 13.7 A practical forest-fire optimisation sequence

1. Keep a correct serial reference and document the RNG equivalence requirement.
2. Choose storage ownership: byte/word groups for packing, or independent byte cells.
3. Preserve old/next separation, halo semantics and timestep synchronization.
4. Make RNG state independent or read-only for concurrent work.
5. Start with contiguous static chunks; compare thread counts.
6. Inspect whether extraction, RNG, branches or memory traffic now dominates.
7. Compare byte-cell SIMD with packed/bitwise approaches using the same intended model.
8. Keep frame writing and diagnostics separate from update-only timing, and also report total time when relevant.

FMA, gather/scatter, removing halos and hand-written bitwise code are possible tools, not milestones that must all appear in the final design.

## 14. Applying this to the matmul assignment

### 14.1 Verified assignment context

The attached file is named `COSC3500_Assignment.pdf`, while its printed heading says **COSC7502 Assignment: Parallel programming techniques**, dated 20 August 2026. This section refers to that supplied document and the adjacent starter files; it does not assume those labels are interchangeable.

The PDF describes three implementations: CPU with AVX/OpenMP, GPU with CUDA, and MPI across two nodes. The performance table uses four CPU cores, one GPU, and two MPI nodes with four cores each. The CPU/MPI references use Intel MKL and the GPU reference uses cuBLAS.

The local headers/build add these practical details:

| Item | Checked value / implication |
|---|---|
| CPU callback | `matrixMultiply(int N, const floatType* A, const floatType* B, floatType* C, int* args, int argCount)` |
| Numeric type | `std::complex<float>` via `FLOATTYPE_COMPLEX64` |
| Allocation alignment | Header specifies `ALIGN=64` for GradeBot CPU allocations |
| Error threshold symbol | `ERR_TOLERANCE`, currently `1e-7` for this type |
| Local default dimension/thread count | N=2048, four threads; these are defaults, not proof of final test dimensions |
| CPU compiler flags | C++11, `-O2 -mavx -fopenmp` in the supplied Makefile |
| Empty input | Starter explicitly handles `N<=0` without accessing buffers |
| Return value | Preserve the required student-ID return contract |
| Include search | Makefile uses cluster `RUB_INC`; local copied headers are evidence, but the cluster header versions determine an actual grading build |

These are local-file facts, not a live verification of the cluster installation.

### 14.2 Rules that affect implementation choices

The PDF specifies that the final editable source files are `matrixMultiply.cpp`, `matrixMultiplyGPU.cu` and `matrixMultiplyMPI.cpp`; only the supplied headers/libraries are permitted, and the submitted functions must not print or write files.

**For these notes:** standalone teaching examples may include ordinary headers. **For the submitted implementation:** adapt them to the supplied interface and permitted transitive declarations; do not assume an extra include, library, C++17 API, changed Makefile or locally enabled ISA will be available to grading.

The presence of MKL/cuBLAS as reference libraries does not make calling them a substitute for the required implementation.

Optional integer args can help tune/debug, but the PDF says the final grading run does not supply your optional arguments. The kernel needs useful defaults when `argCount==0`. Do not hard-code the PDF's illustrative dimension, 13417, as the only supported N.

### 14.3 What an initial CPU implementation should establish

- Correct `C = A*B` for complex values, with no accidental conjugation.
- Correct N=0 handling and required return value.
- Every output element assigned, regardless of its incoming contents.
- Correct nonmultiple dimensions, including vector and tile tails.
- Actual buffer layout and aliasing expectations from the authoritative harness.
- Four-thread behaviour within the supplied allocation/settings, without overriding them from a hardware-core query.

A scalar or row-parallel complex `ikj` kernel is a useful baseline. Each worker owns one or more C rows and processes all k contributions. A shared A/B input is fine. An atomic complex update for every multiplication is neither a simple supported scalar OpenMP atomic nor a good ownership strategy.

### 14.4 A staged optimisation path

| Stage | What to change | What to compare/check |
|---|---|---|
| Baseline | Clear complex scalar matmul | Identity, zeros, hand-calculated complex results, N=0 |
| Traversal | `ikj` with row-local zeroing | Correct outputs and wall time versus baseline |
| Threading | Independent C rows or C tiles | 1/2/4 threads, no shared output contributions |
| Cache reuse | Block i/j/k appropriately | Several tile sizes, edges, setup costs |
| SIMD | Four-complex-value row updates using AVX | Signs/cross terms, unaligned rows, short tails |
| Registers | Hold a C microtile across multiple k values | Spills, throughput and numerical error |
| Packing | Compact selected operand tiles if justified | End-to-end benefit including allocation/copying |

Use the real-float examples to understand the shape of the loops, then use complex arithmetic explicitly. A local `floatType aik` is a complex coefficient; broadcasting its real and imaginary components separately is one AVX strategy.

For N=13417 complex values, a compact row is 107336 bytes. That is 8 modulo 32, so even a 64-byte-aligned matrix base does not give every row 32-byte alignment. At a minimum, aligned-load assumptions must account for both row and column offsets.

### 14.5 Numerical validation and the GradeBot metric

The PDF describes repeated multiplication of random unitary matrices, with the final result compared against the reference. It describes the error output as a sum-of-squares difference and uses `ERR_TOLERANCE` from the rubric header. This is not a blanket per-element allowance of `1e-7`; check the authoritative harness for the precise complex norm/normalisation details.

Consequences:

- Validate repeated products as well as one isolated multiply.
- FMA or a changed reduction order may alter rounding without being mathematically wrong, but still must satisfy the grader's metric.
- Do not enable fast-math casually. It changes mathematical assumptions and exceptional-value behaviour, not just which math library is called.
- Retain the conventional complex multiply signs and avoid conjugation.
- Check finite outputs; a comparison that accidentally treats NaNs as passing is not a correctness check.

The PDF's performance ratio is **time yours / time reference**, so lower is better. The displayed matrices/second measure is throughput, so higher is better. For equivalent work:

```text
runtime ratio = reference matrices/second / your matrices/second
```

This is the inverse orientation of a usual speedup over a slow baseline. Avoid mixing those two ratios in notes.

### 14.6 Cluster-aware testing

The Makefile references cluster paths and CUDA/MPI dependencies. A successful standalone example on this machine is not proof that the full GradeBot builds or passes on Rangpur.

For reference, the documented command shape is:

```sh
./Assignment1_GradeBot N THREADS RUN_CPU RUN_GPU RUN_MPI [optional integers...]
```

Within the proper allocated job/environment, a CPU-only invocation would use `1 0 0` for the three benchmark selectors. Use the provided debug job scripts for the section being developed; the PDF distinguishes these from the full grading script.

No cluster build, GradeBot run, submission or source implementation was performed to create this reference.

## 15. Building, measuring and checking correctness

### 15.1 Build flags and their meanings

For a separate practice file containing the examples and a suitable `main`:

```sh
g++ -std=c++11 -O2 -fopenmp -mavx examples.cpp -o examples
```

For a local experiment on a machine whose instruction set you intend to target:

```sh
g++ -std=c++17 -O3 -fopenmp -march=native \
    -fopt-info-vec-optimized -fopt-info-vec-missed \
    examples.cpp -o examples
```

| Flag | Purpose | Caveat |
|---|---|---|
| `-fopenmp` | Enables OpenMP compilation/linking | Pragmas need compiler/runtime support |
| `-fopenmp-simd` | Enables the supported SIMD subset | Does not enable ordinary thread parallel regions |
| `-mavx` | Allows AVX instructions | Does not imply AVX2 or FMA |
| `-mavx2` | Allows AVX2 | Target CPU/OS must support it |
| `-mfma` | Allows FMA | Check target/build support and numerical results |
| `-march=native` | Targets the compiling machine | Binary may be incompatible with another cluster CPU |
| `-O2` / `-O3` | Optimisation levels | Both can vectorise; exact enabled passes depend on compiler/version |
| `-ffast-math` | Relaxes floating-point assumptions | Can change results/semantics; it is not merely a faster library |

Official references: [GCC OpenMP](https://gcc.gnu.org/onlinedocs/gcc/OpenMP.html), [x86 options](https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html), [optimisation options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html).

The repository's forest-fire Makefile accepts extra `CXXFLAGS`. For example, `make o3 CXXFLAGS='-fopenmp -mavx'` enables those compilation features, but does not itself parallelise the existing serial loop. Avoid using local build overrides as proof of what the assignment grader accepts.

### 15.2 Check whether vectorisation actually happened

Use GCC's `-fopt-info-vec-optimized -fopt-info-vec-missed` to inspect successful and missed loops. [GCC optimisation reports](https://gcc.gnu.org/onlinedocs/gcc/Developer-Options.html).

Typical blockers to investigate:

- loop-carried dependencies;
- ambiguous pointer overlap;
- a stateful RNG call;
- function calls the compiler cannot vectorise/inline;
- complex control flow or unsupported operations;
- gathers/strides too costly for the compiler's model;
- loops too short to amortise setup/tails.

Then inspect the specific hot loop's assembly when needed. `ymm` registers or a vectorisation message elsewhere in the file do not prove the intended loop was optimised. Inlining is a compiler transformation; the C++ `inline` keyword is not a guarantee to substitute the function body. Small readable functions are often inlined without macros.

### 15.3 Time the relevant work

Use wall time for parallel speedup, for example `omp_get_wtime()` around a completed operation, with start/stop read by the same thread. Sum-of-thread CPU time is not elapsed runtime.

Record:

- input size and datatype;
- exact algorithm/layout and tile size;
- compiler/version and flags;
- thread count and affinity;
- machine/CPU and allocated resources;
- RNG strategy/seed for the simulation;
- whether allocation, packing, RNG generation, hashing and I/O are included;
- repeated-run summary and correctness outcome.

Warm up deliberately when measuring steady-state work. Also measure setup-inclusive time when it is part of the workload. Use enough work to dominate timer overhead. Reinitialise C for a `C=A*B` benchmark each run; repeatedly accumulating into stale C changes the workload.

Do not draw performance conclusions from debug `-O0` alone. It is useful for debugging, while optimised builds can change the cost balance substantially. Ensure benchmark results are consumed so the compiler cannot discard the computation.

### 15.4 Speedup and scaling

```text
speedup with P threads = time at 1 thread / time at P threads
efficiency             = speedup / P
```

Use the same algorithm, input and relevant settings to isolate thread scaling. If both algorithm and thread count change, report that as a combined improvement.

Amdahl's law gives an idealised limit when fraction s is serial:

```text
speedup(P) <= 1 / (s + (1-s)/P)
```

Real overhead, bandwidth limits and imbalance can reduce it further. SIMD width times thread count is not a guaranteed overall speedup. More threads can lose to smaller teams when the working set is tiny, memory is saturated or synchronization dominates.

### 15.5 Correctness cases that expose the common mistakes

| Area | Cases to include | Mistake it can expose |
|---|---|---|
| SIMD arrays | 0, 1, width−1, width, width+1, multiple widths+tail | Out-of-bounds vector loads/stores |
| Alignment | A valid deliberately offset pointer | Assuming base/row/tile alignment |
| Matmul | 0/1, odd N, N smaller than tile, nonmultiple N | Empty-input and edge-tile errors |
| Complex arithmetic | `(1+2i)*(3+4i) = -5+10i` | Missing cross terms or wrong signs |
| Matmul state | C initially nonzero | Forgetting to zero or overwrite outputs |
| OpenMP | 1/2/4 threads and more workers than work chunks | Shared scratch, poor decomposition |
| Forest grid | Empty/tree/burning cells, border neighbours, several timesteps | In-place updates or stale halos |
| Packed output | Chunks splitting a byte, row widths not divisible by four | Lost writes to shared storage |
| RNG | Same logical run across thread counts, if promised | Changed draw-to-cell mapping |

Memory sanitizers can detect many out-of-bounds errors in local teaching code. Race-detection tools have compiler/OpenMP-runtime compatibility limits; passing ordinary output tests does not prove race freedom. Use the ownership argument as well as testing.

## 16. Quick reference and common misconceptions

### 16.1 Choose by the problem in front of you

| I need to… | First concept/tool to consider |
|---|---|
| Locate `(row,col)` | Row-major index / leading dimension |
| Use more of each cache line | Contiguous inner traversal |
| Reuse values before eviction | Cache blocking or register blocking |
| Load eight floats | AVX `loadu_ps` or aligned `load_ps` with proof |
| Multiply four complex floats | Interleaved lanes, cross terms, pair swaps and add/sub |
| Vectorise a simple independent loop | Auto-vectorisation / `omp simd` |
| Sum many values | `reduction` |
| Distribute regular rows or tiles | `parallel for schedule(static)` |
| Expose a small outer loop's nested work | `collapse`, after checking ownership |
| Initialise per-worker scratch from an existing value | `firstprivate` |
| Return the logically last loop value | `lastprivate` |
| Update one shared counter occasionally | `atomic update` |
| Retrieve a unique old counter value and increment it | `atomic capture` |
| Update a compound shared invariant | Named `critical` or a lock |
| Wait before consuming a complete grid | Loop-end barrier / `barrier` |
| Swap buffers once | `single` after output completion |
| Run on team thread 0 specifically | `master` / supported `masked` |
| Run a few distinct independent jobs | `sections` |
| Schedule irregular work/dependencies | Tasks, taskwait/taskgroup, depend |
| Retain a generator per worker | Region-local state or deliberately managed `thread_local` |
| Write packed cells safely | Ownership of actual bytes/words |

### 16.2 Corrections worth remembering

- **“Flat array means cache-friendly.”** Only if the traversal has useful locality.
- **“The outer blocking loop loads the tile.”** It selects coordinates; accesses trigger loads.
- **“A tile is a cache line.”** A tile is an algorithmic region, usually spanning many lines.
- **“Cached access is free.”** It still consumes latency/bandwidth and can cause spills/stalls.
- **“Store evicts the vector from cache.”** Ordinary stores do not imply eviction.
- **“A vector declaration reserves a register.”** The compiler allocates registers.
- **“Casting to a vector pointer avoids loads.”** It changes address interpretation; data must still be accessed.
- **“Aligned allocation aligns every element/row.”** Offsets and strides determine derived alignment.
- **“Unaligned means out-of-bounds is okay.”** It relaxes alignment, not size requirements.
- **“Unrolling is SIMD.”** They are different transformations and may be combined.
- **“AVX, AVX2 and FMA are interchangeable.”** They have distinct feature/build requirements.
- **“FMA is necessarily slower.”** Compare useful work, latency, throughput and dependencies.
- **“A complex multiply is lane-wise float multiplication.”** It needs real/imaginary cross terms.
- **“OpenMP creates one thread per iteration.”** A team processes many iterations.
- **“`parallel` divides an ordinary loop automatically.”** Every thread executes the whole block unless work is distributed.
- **“Shared means synchronized.”** It means the same object is used.
- **“Private pointer means private data.”** The pointed-to storage can still be shared.
- **“Different cells always mean different writes.”** Packed cells can share a byte.
- **“Barrier fixes a race.”** It orders phases; it does not repair conflicting accesses within a phase.
- **“Single waits for previous work on entry.”** Its default barrier is at the end.
- **“Atomic read plus atomic write equals atomic update.”** Another worker can interleave between separate operations.
- **“Atomics can replace every critical section.”** Individual atomic operations do not preserve an arbitrary multi-object invariant.
- **“Collapse more loops for more speed.”** Extra loops can introduce races or harm locality.
- **“Fixed per-thread seeds reproduce the old simulation.”** Draw ownership and stream selection also matter.
- **“The old polynomial grid hash is just a sum reduction.”** It is order-dependent; a plain additive reduction changes it.
- **“`-O3` is the only level that vectorises.”** Check the actual compiler; `-O2` can vectorise too.
- **“Fast-math just picks a faster library.”** It changes assumptions and permissible transformations.

## 17. MPI — reserved for later

**Status: not yet studied in the referenced discussions; append the tutorial here later.**

Existing bridge: MPI covers communication between processes, potentially on different nodes. OpenMP covers workers sharing an address space. They can be combined, but this reference does not yet teach MPI APIs.

Topics to add when studied:

- ranks, communicators, process memory and initialisation/finalisation;
- point-to-point sends/receives and deadlock;
- collectives: broadcast, scatter/gather, allgather and reductions;
- blocking/nonblocking operations and communication/computation overlap;
- matrix row/tile decomposition and complex datatypes;
- grid domain decomposition and halo exchange;
- MPI plus OpenMP thread-support levels and resource placement;
- communication costs, strong/weak scaling and correctness.

**Assignment fact to retain for later:** the supplied PDF says every node initially has the full input matrix set. After a distributed product, each node must have the full current product for the next multiply. The MPI design must satisfy that result distribution; input distribution is not required in the way it would be for a single-root input-only setup.

## 18. CUDA — reserved for later

**Status: not yet studied in the referenced discussions; append the tutorial here later.**

Topics to add when studied:

- host/device memory and kernel launches;
- threads, blocks, grids and indexing;
- warps and SIMT, with a careful comparison to CPU SIMD;
- coalesced global access and shared-memory tiling;
- register/shared-memory pressure and occupancy;
- synchronization scope and branch divergence;
- tiled complex matmul and grid/stencil updates;
- transfer costs, CUDA-event timing and correctness checks;
- the assignment's GPU interface and actual available device/build target.

**Assignment fact to retain for later:** the PDF compares the GPU implementation against cuBLAS, but requires the supplied custom GPU function. The local Makefile names `sm_35` and CUDA 11.1 paths; confirm the actual cluster configuration when starting CUDA work rather than assuming these old-looking paths describe the active installation.

## 19. Sources and local reading map

### 19.1 Discussions covered

The duplicated AVX conversation link was treated as one source. Earlier turns were retrieved where needed.

| Conversation | Concepts carried into this reference |
|---|---|
| [Explain OMP Collapse Trick](https://chatgpt.com/c/6aa65de3-1b64-83ec-93fb-b252f46b9228) | Collapse, ownership clauses, atomics, critical regions, barriers, single/master, sections, reductions, SIMD, thread-local RNG |
| [OpenMP IPC Alternatives](https://chatgpt.com/c/6aa53683-e7bc-83ec-aedf-9e725aecbabe) | Shared memory, tasks versus goroutines, absence of channels, MPI bridge |
| [OpenMP thread spawning](https://chatgpt.com/c/6aa535c1-adc4-83ec-956f-61a69f29bad8) | Team creation, all threads executing a block, thread IDs, worksharing |
| [Explain AVX Memory Basics](https://chatgpt.com/c/6aa4ffe8-dc58-83ec-b731-beb558c87045) | Raw allocation, pointer arithmetic, vector values, loads/stores, alignment, aliasing and cache residency |
| [Matmul Array Layout](https://chatgpt.com/c/6aa4efa2-86e8-83ec-b730-79a2a2ecfdad) | Flattening, k reduction, six loop orders, locality, tiles, block-size intuition |

Conversation explanations were consolidated and corrected where necessary. Old performance numbers from slides were not adopted as measurements of this repository.

### 19.2 Local sources checked

Forest-fire source and notes are under `/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim` at the time of writing. The task's earlier `/home/aryan/sem2/COSC3500/forest-fire-sim` path no longer existed.

- [Main simulation loop](/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim/main.cpp)
- [Packed grid accessors](/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim/packed_grid.hpp)
- [PCG implementation](/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim/pcg32.h)
- [Current build settings](/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim/Makefile)
- [Existing SIMD notes](/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim/notes/simd.md)
- [Existing optimisation notes](/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim/notes/optimisation.md)
- [Milestone 2 development notes](/home/aryan/sem2/COSC3500/milestones/milestone1/forest-fire-sim/notes/devlog-m2.md)
- [Supplied assignment PDF](/home/aryan/sem2/COSC3500/assignments/matrix-multiply/COSC3500_Assignment.pdf), visually checked on all three pages
- [CPU starter](/home/aryan/sem2/COSC3500/assignments/matrix-multiply/matrixMultiply.cpp), [CPU header](/home/aryan/sem2/COSC3500/assignments/matrix-multiply/include/matrixMultiply.h), [rubric header](/home/aryan/sem2/COSC3500/assignments/matrix-multiply/include/rubric.h), [assignment Makefile](/home/aryan/sem2/COSC3500/assignments/matrix-multiply/Makefile)

### 19.3 Authoritative references for further lookup

- [OpenMP 5.2 specification contents](https://www.openmp.org/spec-html/5.2/openmp.html) — use the relevant construct's semantics/restrictions; language-version coverage does not imply support in the cluster compiler.
- [OpenMP 5.1 examples](https://www.openmp.org/wp-content/uploads/openmp-examples-5.1.pdf) — worked examples, including synchronization and memory ordering.
- [Intel Intrinsics Guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html) — instruction semantics, ISA requirements and processor-specific performance entries.
- [Clang AVX header reference](https://clang.llvm.org/doxygen/avxintrin_8h.html) — concrete intrinsic definitions and lane operations.
- [GCC optimisation options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html), [vectorisation reports](https://gcc.gnu.org/onlinedocs/gcc/Developer-Options.html), [x86 target options](https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html).
- [C++ complex-number requirements](https://eel.is/c++draft/complex.numbers) — special real/imaginary layout guarantees.

### 19.4 Validation of the teaching examples

The four complete functions (`matmul_blocked`, `add_avx`, `complex_row_update_avx` and `forest_step_bytes`) were extracted directly from this Markdown and compiled with GCC 15.3.1 using C++11, `-O2 -mavx -fopenmp -Wall -Wextra -Werror`.

**Passed: 997 local functional cases across 1, 2 and 4 OpenMP threads**, covering zero/short/odd sizes, SIMD tails, offset input pointers, six tile sizes, initially nonzero C, multiple complex coefficients, and five successive byte-grid updates. The checks also covered the sum/lastprivate examples and sampled PCG skip-ahead positions against serial draws.

AddressSanitizer/UndefinedBehaviorSanitizer validation was attempted but could not link because the local sanitizer runtime libraries were missing. The passing checks above are ordinary functional checks, not sanitizer or race-detector results.

This validates the teaching examples on the local CPU. It does not validate a modified PackedGrid implementation, a complete complex matmul kernel, cluster compatibility, GradeBot correctness or any performance claim.
