# milestone 2 - builds on 1.0 (v0.5)

# v1.0 the baseline

- The baseline is just me running it with o3 and turning on auto vectorise to observe what speedup that gives

# v1.1 - SIMD

We're gonna have to turn our beautiful branching code into a branchless pain in the ass

- we're keeping `grid` and `next` as `std::vector<CellState>` , each cell is already 1 byte.
- a `__m256i` holds 256 bits , so we can load **32 cells at once** instead of 8. the instructions decide whether we're working with 32 byte lanes or 8 32-bit lanes.
  - cell comparisons use `_mm256_cmpeq_epi8` , random comparisons use `_mm256_cmpgt_epi32`.
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
- use unaligned loads/stores to start with , the left and right vectors are shifted by a byte anyway.
- create three vectors with 32 copies of EMPTY , TREE and FIRE. our cell values are `0` , `1` and `2` respectively.
- once we have all 5 vectors loaded , OR the four neighbour vectors together , AND with FIRE , then compare the result with FIRE. call this mask isPropogating.
  - this works with our encoding because only FIRE has the `0b10` bit set.
  - the equality check turns `2` into `0xFF` for true , or `0` into `0x00` for false. now it's consistent with the rest of our byte masks.

- for the 32 cells we are processing , let's call it current vector. we do
  - current == EMPTY -> candidates for tree growth , call it isEmpty
  - current == TREE -> candidates for combusting , call it isTree
  - current == FIRE -> burning cells that must become empty , call it isToBeEmpty

- now the slightly annoying bit. `pcg32_8.h` gives us **8 random numbers at once , each 32 bits**. so we call `nextfloat()` 4 times for our 32 cells:

```text
current : [ cells 0-7 | cells 8-15 | cells 16-23 | cells 24-31 ]
randoms :     rng0        rng1          rng2           rng3

32 cells   x  8 bits =  256 bits -> one __m256i
32 randoms x 32 bits = 1024 bits -> four __m256i
```

- we can do this in an inner loop running 4 times. each iteration gets 8 random numbers and compares them against both thresholds , using the same randoms for growth and fire.
  - repeat `p_threshold` across 8 32-bit lanes , and do the same for `f_threshold`. these are the integer thresholds we already calculate from p(tree) and p(fire).
  - for each batch , random < f_threshold gives us 8 masks for which spots can burn.
  - random < p_threshold gives us 8 masks for which spots can grow.
  - RNG values are unsigned 32-bit , but `_mm256_cmpgt_epi32` is signed. XOR both the randoms and threshold with `0x80000000` first , then compare **threshold > random** to get random < threshold.

- these comparisons give us **32-bit masks** , but our cell masks are **8-bit**. so we pack the comparison results down to bytes , then combine the 4 batches in cell order.
  - true goes from `0xFFFFFFFF` to `0xFF` , false stays zero.
  - we're packing the comparison results , not chopping the random numbers into bytes. that keeps the probability precision , especially for small p(fire).

```text
example for one batch , with an integer threshold of 100:

randoms : [ 10 | 150 | 99 | 100 | 12 | 200 | 45 | 101 ]
< 100   : [  T |   F |  T |   F |  T |   F |  T |   F ]
as bytes: [ FF |  00 | FF |  00 | FF |  00 | FF |  00 ]

combine the four batches:

isGrowing : [ 8 byte masks | 8 byte masks | 8 byte masks | 8 byte masks ]
isEmpty   : [                32 byte masks in cell order               ]

now each byte in isGrowing lines up with the same cell in isEmpty.
```

- do this for both thresholds to get one 32-byte isGrowing vector and one 32-byte isBurning vector.
  - `_mm256_packs_epi32` then `_mm256_packs_epi16` can shrink the masks from 32 -> 16 -> 8 bits. use signed packing so true stays all ones (`-1`).
  - AVX2 packs within each 128-bit half , so the result needs rearranging into cells 0-31 order. don't assume the packs just concatenate the batches. [packing reference](https://clang.llvm.org/doxygen/avx2intrin_8h.html)

- We then do a couple bitwise ANDS
  - isEmpty AND isGrowing -> all spots that will have tree growth , call it TreeGrowth
  - (isPropogating OR isBurning) AND isTree -> all trees that will burn , call it TreeBurning

- finally we propagate it to the `next` grid state.
  - nextVector = current
  - use TreeBurning to select FIRE in the matching lanes.
  - use TreeGrowth to select TREE in the matching lanes.
  - use isToBeEmpty to select EMPTY in the matching lanes.
  - `_mm256_blendv_epi8` can do these selections. the masks are `0xFF` / `0x00` , **not cell values** , so don't store the masks themselves as the next state.
  - store the 32 updated cells into `next`.

- and then we load in the next 32 cells and do it again.
  - x advances by **1 row** , y advances by **32 cells**. only process full batches inside the row , then handle any leftover interior cells separately so we don't overwrite the border.
  - swap `grid` and `next` once after the whole grid is done , then save the frame.
  - `pcg32_8` uses 8 parallel RNG streams , so we shouldn't expect the same grid hash as the scalar RNG baseline.
