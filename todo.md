<!--1. **Skip RNG generation for `Burning` cells** — one-line move. _Breaks existing checksums — own version._-->
<!--2. **Skip RNG generation for `Tree` cells with a burning neighbor** — same idea, same checksum caveat.-->
4. **Integer threshold compare instead of float** — precompute `p_threshold`/`f_threshold`, compare against `nextUInt32()` directly.
5. **Flatten grid to 1D** — the big one; rewrite indexing, redo checksum for new layout.
6. **Strength reduction on flattened index math** — depends on #5.
7. **Manual loop unrolling** — depends on #5/#6; watch the padded boundary.
8. **Manual 2-bit packing** — new accessor layer, neighbor-counting rewrite, own checksum pass, likely needs its own strength-reduction/unrolling redo.

- 4096×4096 grid goes from 16 MB down to 4 MB with this. benchmark the size reduction of the grid and cache hit/miss

9. **(Stretch) Merge `grid`/`next` into a single buffer** — only if time permits; correctness-risky (breaks synchronous update semantics unless done very carefully) and likely a cache-locality _regression_ rather than a win, so treat it as a "tried it, here's why it didn't pan out" experiment for the reflection section rather than an expected speedup.
