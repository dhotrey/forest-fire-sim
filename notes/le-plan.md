# milestone 2 - le plan

get SIMD working first , mess with performance after that , then scale it with OpenMP + MPI.

the actual SIMD walkthrough is in [devlog-m2.md](devlog-m2.md). this is the order to work through it. we're using `nextFloat()` for the first working version , the integer threshold approach in the devlog is a later experiment.

## SIMD - one thing at a time

1. [ ] make sure the debug build has AVX2 enabled too , not just the o3 build. we need the debug build for checking hashes.
2. [ ] use **5120 x 5120 interior cells** , plus the border. allocated width is **5122** , each interior row has exactly **160 batches of 32**. keep `grid` and `next` as byte-sized `std::vector<CellState>`.
3. [ ] fix the loops in `main.cpp` : x advances by **1 row** , y by **32 cells**. swap the grids and save the frame after the whole grid is done , not after each row.
4. [ ] create the EMPTY , TREE and FIRE vectors with 32 copies of each cell value. use `0` , `1` and `2` respectively.
5. [ ] load 32 current cells using `_mm256_loadu_si256` and `grid.data() + index`. no unpacking or numeric conversion needed.
6. [ ] load the four neighbour vectors the same way : above at `index - grid_size` , below at `index + grid_size` , left at `index - 1` , right at `index + 1`. just use overlapping loads for now , the CPU handles caching.
7. [ ] compare current with EMPTY , TREE and FIRE using byte comparisons. get isEmpty , isTree and isToBeEmpty , each with 32 masks of `0xFF` / `0x00`.
8. [ ] build isPropogating : OR the four neighbours , AND with FIRE , then compare with FIRE so this is also a proper byte mask.
9. [ ] decide the RNG mapping before recording our reference hash. attach seeded streams to fixed global rows or blocks so changing thread/process counts later won't change which random value each cell gets. keep those streams advancing across timesteps.
10. [ ] generate randomness in an inner loop running **4 times**. each `nextFloat()` returns a `__m256` with 8 floats in **[0, 1)** , enough for the next 8 cells in our batch.
11. [ ] broadcast p and f once before the timestep loop with `_mm256_set1_ps(static_cast<float>(p))` and the same for f. compare each random batch directly against both using `_mm256_cmp_ps(randoms, pVector, _CMP_LT_OQ)` and the same for f. reuse the same randoms for both checks , no integer thresholds or sign-bit XOR needed for now.
12. [ ] keep the four growth masks and four fire masks. the float comparisons already give **0xFFFFFFFF / 0** per 32-bit lane. use `_mm256_castps_si256` to treat those same bits as integer masks , then use signed packing from **32 -> 16 -> 8 bits** to get one 32-byte isGrowing vector and one isBurning vector. this cast doesn't numerically convert the mask values.
13. [ ] keep the packing's natural RNG-to-cell order for now , no permutation. pack growth and fire identically so each cell uses the same random value for both checks. use a deliberately mixed true/false pattern to check that mapping.
14. [ ] combine the masks : `TreeGrowth = isEmpty AND isGrowing` , `TreeBurning = isTree AND (isPropogating OR isBurning)`.
15. [ ] start nextVector from current. select FIRE for TreeBurning , TREE for TreeGrowth , EMPTY for isToBeEmpty. use the masks to select cell values , don't store `0xFF` as a cell state.
16. [ ] store the 32 updated cells into `next` using an unaligned store. only write interior cells , leave the border empty.
17. [ ] check the update on a small grid with an interior width divisible by 32. cover growth , spontaneous fire , fire spreading across batch/row boundaries , and burning cells becoming empty. compare against hand-worked updates or scalar updates given the same random values.
18. [ ] check the border stays empty separately , since the existing hash only covers interior cells. move the hash print outside the timestep loop so it checks the final frame.
19. [ ] run the working SIMD version repeatedly with fixed inputs/seeds and save the final hash with those settings. this is our reference for OpenMP , MPI and experiments that preserve the RNG mapping and comparison rule. the old scalar RNG hash isn't expected to match the new RNG streams.
20. [ ] benchmark the working 32-cell kernel against the o3 / auto-vectorised baseline using the same grid size , timestep count and probabilities. keep visualisation off for timing.

## experiments - after it works

- [ ] check `lscpu` on the actual compute node inside a Slurm job. record the CPU , cache details , compiler and build flags with the results.
- [ ] add the permutation after packing both probability masks and compare against the natural packed order. time packing with/without permutation on identical mask inputs to isolate its overhead. the full simulation assigns random draws to different cells with the permutation , so record its own reference hash.
- [ ] compare `nextFloat()` against `nextUInt()` with 32-bit integer thresholds and unsigned-safe comparisons. `nextFloat()` uses the same RNG step plus float construction , with 23 random bits per value. benchmark whether avoiding that construction helps , don't assume the integer version is faster. probability precision changes , so validate that version separately and record its own reference hash.
- [ ] after that , try **2 RNG calls with 16 bits per cell** instead of 4 calls with 32 bits. measure the speedup and probability rounding separately , with its own correctness check and reference hash.
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
