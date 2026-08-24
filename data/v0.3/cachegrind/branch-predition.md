# v0.3 branch-prediction investigation

## Setup

Both binaries were compiled with GCC 8.5.0 using `-O2` and run under
Valgrind 3.26.0 Cachegrind with branch simulation enabled and cache simulation
disabled:

```sh
valgrind --tool=cachegrind --cache-sim=no --branch-sim=yes \
  ./bin/fire-v0.3-o2 1000 500 0.02 0.01

valgrind --tool=cachegrind --cache-sim=no --branch-sim=yes \
  ./builds/v0.2/fire-v0.2-o2 1000 500 0.02 0.01
```

The requested 1000 by 1000 grid receives a one-cell padding border internally,
which is why the program reports a grid size of 1002. The simulation performs
500,000,000 interior-cell updates.

## Results

| Metric | v0.2 `-O2` | v0.3 `-O2` | Change |
| --- | ---: | ---: | ---: |
| Instruction references | 15,306,357,873 | 16,221,531,044 | +915,173,171 (+6.0%) |
| Branches | 1,872,193,132 | 2,359,083,727 | +486,890,595 (+26.0%) |
| Conditional branches | 1,872,176,629 | 2,359,067,224 | +486,890,595 (+26.0%) |
| Indirect branches | 16,503 | 16,503 | no change |
| Mispredictions | 159,425,716 | 168,173,217 | +8,747,501 (+5.5%) |
| Conditional mispredictions | 159,424,722 | 168,172,223 | +8,747,501 (+5.5%) |
| Indirect mispredictions | 994 | 994 | no change |
| Misprediction rate | 8.5% | 7.1% | -1.4 percentage points |

Although v0.3 has a lower misprediction *rate*, it executes many more branches
and therefore has more mispredictions in absolute terms. Mispredictions per
thousand instruction references are almost unchanged: approximately 10.42 for
v0.2 and 10.37 for v0.3. This does not support worse prediction accuracy as the
main cause of the regression.

The additional 486,890,595 branches equal about 0.974 extra branches per cell
update. The additional branches produce an approximately 1.8% misprediction
rate, which is close to the 1% and 2% probability thresholds used for lightning
and growth. This is consistent with GCC 8.5 emitting a conditional branch for
nearly every probability test in v0.3, while the simpler v0.2 loop allowed
`-O2` to turn more of those decisions into branchless operations.

## Likely explanation

Moving `rng.nextFloat()` from one unconditional location into the Empty and
Tree paths reduces the number of random values generated, but it also makes RNG
state advancement conditional on the cell-state control flow. The more complex
control-flow graph appears to prevent an effective `-O2` transformation that
v0.2 received. Possible contributing effects are lost if-conversion, duplicated
inlined RNG code, additional control dependencies, and less opportunity to
overlap RNG arithmetic with grid loads.

This explains why v0.3 improves the `-O1` result but regresses at `-O2`: at
`-O1`, avoiding some RNG work is beneficial, while at `-O2` that saving is
outweighed by 6% more executed instructions and 26% more dynamic branches.

The result is strong evidence of a GCC 8.5 code-generation interaction, but it
is not complete proof of one specific compiler transformation. Skipping random
numbers also changes which random value is assigned to each later cell, so v0.2
and v0.3 follow different stochastic trajectories. Line-level Cachegrind output
or disassembly would be required to separate compiler effects from differences
in the visited cell-state paths.

## Conclusion

The conditional-RNG change is not a performance improvement for the target
GCC 8.5 `-O2` build. v0.2 remains faster overall. The most likely reason is that
the small reduction in RNG work is outweighed by substantially more generated
work in the hot loop, especially nearly one additional dynamic branch per cell
update. Further investigation is possible, but more direct optimisations should
be prioritised first.
