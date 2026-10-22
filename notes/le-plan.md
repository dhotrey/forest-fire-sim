# milestone 2 - le plan

get SIMD working first , mess with performance after that , then scale it with OpenMP + MPI.

the actual SIMD walkthrough is in [devlog-m2.md](devlog-m2.md). the first version uses `nextFloat()` and the packing's natural RNG-to-cell order , no permutation. integer RNG and the permutation are experiments for v1.2.

## v1.0 - serial baseline

- [x] keep `serial.cpp` as **v1.0 serial-baseline**. `make serial` builds `bin/fire-v1.0-serial-baseline-o3` with `-O3 -march=native` , even if the SIMD version changes.

## v1.1 - SIMD , one thing at a time

1. [x] make sure the debug build has AVX2 enabled too , not just the o3 build. we need the debug build for checking hashes.
2. [x] use **5120 x 5120 interior cells** , plus the border. allocated width is **5122** , each interior row has exactly **160 batches of 32**. keep `grid` and `next` as byte-sized `std::vector<CellState>`.
3. [x] fix the loops in `main.cpp` : x advances by **1 row** , y by **32 cells**. swap the grids and save the frame after the whole grid is done , not after each row.
4. [x] create the EMPTY , TREE and FIRE vectors with 32 copies of each cell value. use `0` , `1` and `2` respectively.
5. [x] load 32 current cells using `_mm256_loadu_si256` and `grid.data() + index`. no unpacking or numeric conversion needed.
6. [x] load the four neighbour vectors at offsets `-1` , `+1` , `-grid_size` and `+grid_size`. just use overlapping loads for now , the CPU handles caching.
7. [x] compare current with EMPTY , TREE and FIRE using byte comparisons. get isEmpty , isTree and isToBeEmpty , each with 32 masks of `0xFF` / `0x00`.
8. [x] build isPropogating : OR the four neighbours , AND with FIRE , then compare with FIRE so this is also a proper byte mask.
9. [ ] before OpenMP / MPI , attach RNG streams to fixed global rows or blocks so changing thread/process counts won't change which random value each cell gets. currently we have one `pcg32_8` object advancing through the whole grid.
10. [x] generate randomness in an inner loop running **4 times**. each `nextFloat()` returns a `__m256` with 8 floats in **[0, 1)** , enough for the next 8 random checks in our batch.
11. [x] broadcast p and f once before the timestep loop with `_mm256_set1_ps(static_cast<float>(p))` and the same for f. compare each random batch directly against both using `_mm256_cmp_ps(randoms, pVector, _CMP_LT_OQ)` and the same for f. reuse the same randoms for both checks , no integer thresholds or sign-bit XOR needed for now.
12. [x] keep the four growth masks and four fire masks in `__m256i` arrays. use `_mm256_castps_si256` on the float comparison results , then two `_mm256_packs_epi32` calls and one outer `_mm256_packs_epi16` per probability. that shrinks **32 -> 16 -> 8 bits** , keeping true as all ones. the cast preserves bits , it doesn't numerically convert them.
13. [x] keep the packing's natural RNG-to-cell order , no permutation. pack growth and fire identically so each cell uses the same random value for both checks. this is a chosen assignment of random draws , not a rule violation or extra entropy.
14. [x] combine the masks : `treeGrowing = isEmpty AND isGrowing` , `treeBurning = isTree AND (isPropogating OR isBurning)`.
15. [x] start nextVector from current. use `_mm256_blendv_epi8` to select TREE for treeGrowing , FIRE for treeBurning , EMPTY for isToBeEmpty. all masks come from the original current vector , so new trees don't burn in the same timestep.
16. [x] store the 32 updated cells into `next` using `_mm256_storeu_si256`. only write interior cells , leave the border empty.
17. [ ] finish the small-grid checks : mixed true/false masks , isolated fire spreading across batch/row boundaries , and scalar updates given the same mapped random values. the deterministic checks below passed , but don't cover all of this.
18. [x] check the border stays empty separately , since the existing hash only covers interior cells. move the hash print outside the timestep loop so it prints once for the final frame.
19. [ ] run the working SIMD version repeatedly with fixed inputs/seeds and save the final hash with those settings. this is our reference for OpenMP , MPI and experiments that preserve the RNG mapping and comparison rule. the old scalar RNG hash isn't expected to match the new RNG streams.
20. [x] benchmark `make o3` against `make serial` using the same grid size , timestep count and probabilities. keep visualisation off for timing and record the RNG / probability precision differences alongside the speedup.

done so far : both debug builds compile , all six deterministic runs on 32 / 64-cell interior widths passed (`p=0,f=0` , `p=1,f=0` , `p=1,f=1`). the saved three-frame tree -> fire -> empty sequence and its borders passed too , and i've run and visualised the normal version as a sanity check.

## v1.2 - RNG + mask experiments

- [ ] check `lscpu` on the actual compute node inside a Slurm job. record the CPU , cache details , compiler and build flags with the results.
- [ ] add the permutation after packing both probability masks and compare against the natural packed order. time packing with/without permutation on identical mask inputs to isolate its overhead. the full simulation assigns random draws to different cells with the permutation , so record its own reference hash.
- [ ] compare `nextFloat()` against `nextUInt()` with 32-bit integer thresholds and unsigned-safe comparisons. `nextFloat()` uses the same RNG step plus float construction , with 23 random bits per value. benchmark whether avoiding that construction helps , don't assume the integer version is faster. probability precision changes , so validate that version separately and record its own reference hash.
- [ ] after that , try **2 RNG calls with 16 bits per cell** instead of 4 calls with 32 bits. measure the speedup and probability rounding separately , with its own correctness check and reference hash.

## other performance experiments

- [ ] try processing **64 and 128 cells per iteration** : two or four 32-cell SIMD batches. this is loop unrolling , not a bigger SIMD register or cache line.
- [ ] try explicit prefetching **64 / 128 / 256 cells ahead** for the three source rows. request future data while processing the current batch , then compare against hardware prefetching alone.
- [ ] optionally compare the direct left/right loads against constructing neighbour vectors with shuffles and the missing end cells. don't assume fewer loads means faster.
- [ ] change one thing at a time , repeat the timings and compare against the plain 32-cell version. for unrolling , prefetching and neighbour-load changes , keep the RNG-to-cell mapping unchanged and require the final hash to match.

## OpenMP - rough plan

- [ ] divide rows between threads , keeping the SIMD update inside each thread.
- [ ] give each thread exclusive output rows. keep the global row/block RNG mapping , no shared mutable RNG.
- [ ] synchronise after the grid update , then swap once per timestep.
- [ ] compare the final hash across thread counts and measure scaling.

## MPI - rough plan

- [ ] divide the grid into row bands , keeping global row indices for RNG mapping.
- [ ] exchange current-state halo rows each timestep. only the outer edges of the global grid stay permanently empty.
- [ ] update each process's own rows with the SIMD kernel , then try OpenMP within each process.
- [ ] assemble the final grid in global row order and use the existing hash. compare across process counts , then measure MPI and combined OpenMP + MPI scaling.
