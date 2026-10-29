# milestone 2 - builds on 1.0 (v0.5)

# v1.0 the baseline

- The baseline is `serial.cpp` built with `-O3 -march=native` , allowing the compiler to auto vectorise. `make serial` always builds it as **v1.0 serial-baseline** in `bin/fire-v1.0-serial-baseline-o3`.
- we're comparing the SIMD version against these same rules : empty cells can grow , trees catch fire from a neighbour or randomly , burning cells become empty. all updates read the old grid.

# v1.1 - SIMD

We're gonna have to turn our beautiful branching code into a branchless pain in the ass

- the SIMD run won't have the same hash as this baseline : it uses different RNG streams/seeds and float probability checks instead of the scalar integer thresholds. the rules match , the exact random trajectory doesn't.
- the first kernel is now implemented in `main.cpp`. we're using floats for the probability checks to get it working first , integer comparisons can wait for v1.2.
- we're keeping `grid` and `next` as `std::vector<CellState>` , each cell is already 1 byte.
- the workload is **8320x8320 interior cells** , with padding on top of that. allocated width is 5122 , so we get exactly 160 batches per interior row and don't need a leftover-cell path for this workload.
- a `__m256i` holds 256 bits , so we can load **32 cells at once** instead of 8. the instructions decide whether we're working with 32 byte lanes or 8 32-bit lanes.
  - cell comparisons use `_mm256_cmpeq_epi8` , random float comparisons use `_mm256_cmp_ps`.
  - 32 cells at once doesn't automatically mean 4x the speedup , we still have to generate and compare 32 random numbers.

- for the 32 cells loaded we also need the 32 cells above , below , left and right of each cell.
- say `i = x * width + y` , and `[start:end]` excludes the end index:

```text
current : [i : i+32]
above   : [i-width : i-width+32]
below   : [i+width : i+width+32]
left    : [i-1 : i+31]
right   : [i+1 : i+33]
```

- that's 5 vectors , each holding 32 cells. lane 0 in each neighbour vector belongs to lane 0 in current , and so on.
- load them with `_mm256_loadu_si256(reinterpret_cast<const __m256i*>(grid.data() + i))` and the matching neighbour offsets. that's a raw 32-byte read , no numeric conversion or unpacking.
- use unaligned loads/stores to start with , the left and right vectors are shifted by a byte anyway. the overlapping loads don't allocate more grid memory , the CPU handles cache reuse.
- create three vectors with 32 copies of EMPTY , TREE and FIRE. our cell values are `0` , `1` and `2` respectively.
- once we have all 5 vectors loaded , OR the four neighbour vectors together , AND with FIRE , then compare the result with FIRE. call this mask isPropogating.
  - this works with our encoding because only FIRE has the `0b10` bit set.
  - the equality check turns `2` into `0xFF` for true , or `0` into `0x00` for false. now it's consistent with the rest of our byte masks.

- for the 32 cells we are processing , let's call it current vector. we do
  - current == EMPTY -> candidates for tree growth , call it isEmpty
  - current == TREE -> candidates for combusting , call it isTree
  - current == FIRE -> burning cells that must become empty , call it isToBeEmpty

- now the slightly annoying bit. `pcg32_8.h` gives us **8 random floats in [0, 1) at once** through `nextFloat()`. each float takes 32 bits , so we call it 4 times inside each 32-cell update:

```text
call 0 : random results  0-7
call 1 : random results  8-15
call 2 : random results 16-23
call 3 : random results 24-31

32 cells   x  8 bits =  256 bits -> one __m256i
32 floats  x 32 bits = 1024 bits -> four __m256
```

- broadcast p and f once before the timestep loop using `_mm256_set1_ps(static_cast<float>(p))` and the same for f. this gives us 8 copies of each probability.
- the inner RNG loop runs 4 times. each iteration compares the same 8 random floats against both p and f using `_mm256_cmp_ps(randoms, pVector, _CMP_LT_OQ)` and the same for f.
  - `_CMP_LT_OQ` is our less-than comparison. random < p gives growth checks , random < f gives fire checks.
  - no integer thresholds or sign-bit XOR in this version. `nextFloat()` uses 23 random bits per value , so this has less probability resolution than the 32-bit integer version.
  - save the results in `__m256i growthChecks[4]` and `fireChecks[4]`. these are arrays of 4 vectors , each containing 8 comparison masks , not arrays of the original random floats.
  - the comparison returns `__m256` , so use `_mm256_castps_si256` when saving it. this preserves the bits for integer packing , no numeric conversion.

- these comparisons give us **32-bit masks** , but our cell masks are **8-bit**. so we pack the comparison results down to bytes.
  - true goes from `0xFFFFFFFF` -> `0xFFFF` -> `0xFF` , false stays zero.
  - we're shrinking the comparison results , not the random values , so packing doesn't lose any of the true/false information.

```text
example for one batch , with p = 0.02:

randoms : [ .001 | .03 | .019 | .02 | 0  | .5 | .01 | .99 ]
< p     : [   T  |  F  |   T  |  F  | T  | F  |  T  |  F  ]
as bytes: [  FF  | 00  |  FF  | 00  | FF | 00 | FF  | 00  ]
```

- do this for both probabilities to get one 32-byte isGrowing vector and one isBurning vector.
  - two `_mm256_packs_epi32` calls combine batches 0/1 and 2/3 into 16-bit masks. one outer `_mm256_packs_epi16` combines those into byte masks. use signed packing so true stays all ones (`-1`).
  - AVX2 packs within each 128-bit half , so the random results don't come out in the original draw order. [packing reference](https://clang.llvm.org/doxygen/avx2intrin_8h.html)

```text
random result indices after packing:
[ 0-3 | 8-11 | 16-19 | 24-27 | 4-7 | 12-15 | 20-23 | 28-31 ]

the physical cells those byte masks are applied to:
[ 0-3 | 4-7  | 8-11  | 12-15 | 16-19 | 20-23 | 24-27 | 28-31 ]
```

- we're keeping this natural packed order , no permutation for now. so cell 4 gets random result 8 rather than result 4 , for example. both growth and fire use the exact same packing so the two checks still share one random value per cell. the state/neighbour masks themselves stay in physical cell order.

- We then do a couple bitwise ANDS
  - isEmpty AND isGrowing -> all spots that will have tree growth , call it treeGrowing
  - (isPropogating OR isBurning) AND isTree -> all trees that will burn , call it treeBurning. the isTree part matters , empty cells can't just catch fire.

- finally we propagate it to the `next` grid state.
  - nextVector = current
  - use treeGrowing to select TREE in the matching lanes.
  - use treeBurning to select FIRE in the matching lanes.
  - use isToBeEmpty to select EMPTY in the matching lanes.
  - `_mm256_blendv_epi8(nextVector, treeVector, treeGrowing)` keeps the byte from nextVector when the mask is `0x00` , takes it from treeVector when the mask is `0xFF`. do the same for fire and empty.
  - all masks come from the original current vector. a new tree doesn't burn in the same timestep , and a newly burning tree doesn't immediately become empty.
  - the masks are **not cell values** , so don't store them as the next state. `_mm256_storeu_si256` writes the 32 updated cell values into `next` , the old `grid` stays untouched until the swap.

- and then we load in the next 32 cells and do it again.
  - x advances by **1 row** , y advances by **32 cells**. the interior width must be divisible by 32 for this implementation , arbitrary leftover widths aren't handled.
  - swap `grid` and `next` once after the whole grid is done , then save the frame.
  - print the hash once after all timesteps , not after every row or timestep.

- both debug builds compile. six deterministic runs passed on 32 / 64-cell interior widths : staying empty , growing and staying trees , and the tree -> fire -> empty sequence.
- checked the saved three-frame sequence and empty borders too. i've also run and visualised the normal version and it looks alright , but mixed-pattern / same-random scalar checks are still on le-plan before calling the validation finished.
- currently there's one default-seeded `pcg32_8` object for the whole grid. before OpenMP / MPI we still need RNG ownership tied to global rows/blocks , then save a repeatable reference hash for that mapping.

# v1.2 - RNG + mask experiments

I'll try to unroll the rng loop, I'll also run gprof , valgrind , cachegrind , measuing branch predictions and what not.
After doign the above i didn't see many useful findins

- loop unroll does basically nothing (0.6% improvement) so i think the compiler does it better - not gonna include in the presentation
- valgrind/cachegrind/callgrind also show very little to help

- gonna try and unroll the y loop to process 64 elements in one go to see how that goes for me
  - unrolled the loop 4 times and got a 1% speedup , nice - idt worth speaking about. moving onto next version.

# v1.3 - openmp

- spread work across threads aha!
- going to run and record the speedup when ran across 2/4/6/8 threads

# v1.x - better simd kernel?

Will try to improve the simd kernel i have here.

- Detect burning neighbours with one comparison
- Construct the output directly instead of blending three times
- We'll compare `nextFloat()` against 32-bit integer RNG checks ,
- then try halving it to 2 RNG calls with 16 bits per cell and measure the speed / probability precision tradeoff.
