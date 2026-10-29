# Milestone 2 animations

## Full presentation

Open `milestone2.html` for the full 17-slide presentation matching
`script-milestone-2.md`. Use the arrow keys to advance conceptual stages and
Space to pause/resume a video. Every animation stage finishes and holds until
the presenter advances. Videos play at normal speed. The counter shows the
script slide number, including when a slide contains several animation stages.

Direct links use stable script IDs: `milestone2.html#/s8` opens the completed
RNG comparison arrays, `#/s10` opens blending, and `#/s12` opens OpenMP.
The original introductory forest-fire GIF still loops.

The final sequence is title, simulation rules, methodology/build information,
serial baseline, branchless AVX introduction, 32-byte load, neighbour masks,
RNG/packing, rule masks, blending, AVX results, OpenMP implementation, scaling,
combined results, correctness reflection/conclusion, AI disclosure, and bibliography.
The closing slides are `#/s16` for AI disclosure and `#/s17` for the references,
including Manim Community v0.19.0.

Final-script S9 is a static slide with the `treeGrowing`, `treeBurning` and
`isToBeEmpty` masks, each below its rule in plain English. It contains no current
vector, intrinsics or animation stages. The exporter saves its rendered layout
as `assets/rule-masks.png` and embeds that image in the deck.

Final-script S10 is also static: it shows the three blending instructions and
the mask-selection explanation. It has no store instruction or vector diagrams.
The exporter embeds its rendered layout from `assets/blending.png`.

Rebuild the animations and the complete offline HTML from this directory:

```sh
bash build.sh '/home/aryan/Downloads/COSC3500 - Milestone 2.pptx'
```

`final_slides.py` contains the combined methodology scene and all new rule,
blending, results, OpenMP and closing scenes. The three result slides use the
existing chart PNGs in `plots/benchmarks`. The correctness reflection distinguishes
different RNG trajectories from checking the update rules and from a scalar
comparison with matched random inputs.

The title, simulation, baseline and AVX-introduction slides preserve their
PowerPoint layouts as rendered images. Methodology uses the original node/build
screenshots with corrected text: 8320 cells per side, five runs, and no claim
of warm-ups. Edit the original PowerPoint, then run the import again to refresh
the original layouts after the animations have been rendered:

```sh
.venv/bin/python port_intro.py '/home/aryan/Downloads/COSC3500 - Milestone 2.pptx'
```

The source PowerPoint and animation sources are separate from the generated full deck.
The full HTML includes all its media and works offline.

## S7

Open `milestone2.html#/s6` in a browser. Use the right arrow to advance and the left arrow
to go back. Space pauses or resumes the current animation. Each animation
finishes and holds until you advance.
The HTML includes its videos and presentation assets, so it works offline.

The two stages follow final-script S6:

1. Write the load instruction and show a 256-bit register.
2. Reveal the one-byte `CellState` type and divide the register directly into
   32 byte lanes, numbered 0 to 31, in one animation.

The lane numbers indicate positions, not cell-state values. The load copies
32 bytes; this scene does not claim a 32-times speedup or show state updates.
The layout uses a white background and leaves the bottom-right corner clear
for the face recording.

Use the rebuilt `milestone2.html#/s6` when recording. Standalone HTML and preview
files from earlier work are not refreshed by the final-deck build.

## Render again

Run these commands from this directory, using the existing local environment:

```sh
.venv/bin/manim render -r 1920,1080 --fps 30 s7_avx.py S7AVX
cp media/videos/s7_avx/1080p30/S7AVX.mp4 s7-preview.mp4
XDG_CACHE_HOME="$PWD/.cache" .venv/bin/manim-slides convert S7AVX s7.html --one-file --offline -creveal_theme=white -cbackground_color=white -ccontrols=true -cmargin=0
```

## S8

S8 shows the five-cell neighbourhood, a labelled grid, the five 32-byte loads,
and bitwise OR of the four neighbour vectors. Four manual stages cover the
neighbourhood, the grid and all five loads, the OR inputs and result together,
and the final combined bits. S9's fire-bit extraction also advances manually.
Together these scenes form script S7.
Rebuild S8 and the combined deck with:

```sh
.venv/bin/manim render -r 1920,1080 --fps 30 s8_neighbours.py S8Neighbours
.venv/bin/python port_intro.py '/home/aryan/Downloads/COSC3500 - Milestone 2.pptx'
```

The illustrative grid uses 20 rows and 36 columns so the 32-cell batch and its
one-cell left/right offsets fit. Values use a fixed seed and every extracted
vector comes from that grid. The drawing places increasing row indices upward
to match `main.cpp`'s `up = idx + grid_size` naming. The devlog's above/below
diagram uses the opposite drawing orientation; the four inputs to OR are the
same. No grid cells are updated in this scene.

Bitwise OR preserves both state bits: tree `01` OR fire `10` gives `11`, or
decimal 3. This is a combined bit field, not a fourth cell state or a final
ignition mask. The subsequent AND/equality checks are shown in S9.

## S9

S9 carries over S8's 32 OR results, broadcasts 2 into `fireVector`, ANDs the
vectors to get `fireBits` in one animation, then pauses before a second animation
that compares each byte against 2, shows the equality mask and presents the
completed neighbour-fire mask. The equality
result displays `FF` or `00` in hexadecimal, meaning all one bits or all zero
bits. It marks cells with a burning neighbour; later cell-state checks decide
which current cells ignite.

```sh
.venv/bin/manim render -r 1920,1080 --fps 30 s9_fire_mask.py S9FireMask
.venv/bin/python port_intro.py '/home/aryan/Downloads/COSC3500 - Milestone 2.pptx'
```

## S10

S10 begins with the completed `growthChecks[4]` and `fireChecks[4]` arrays, the
state formerly shown at HTML index `#/33`. The earlier eight-float walkthrough
is retained as the optional `RNGWalkthrough` class and omitted from the final deck.
Each array entry is a vector of eight 32-bit masks. True is `FFFFFFFF`, false
is `00000000`; T/F in the array overview abbreviate those exact bit patterns.
The cast preserves comparison bits. Packing into bytes is shown in S11.

The example values are illustrative, converted to float32, with `p=0.02` and
`f=0.01`. They are not a recorded PCG output sequence. Values equal to the
threshold fail the strict less-than test. The four RNG calls happen within
each 32-cell update, and the threshold broadcasts happen before the timestep loop.

```sh
.venv/bin/manim render -r 1920,1080 --fps 30 s10_rng_checks.py S10RNGChecks
.venv/bin/python port_intro.py '/home/aryan/Downloads/COSC3500 - Milestone 2.pptx'
```

## S11

S11 has two presenter-controlled stages: the unpacked comparison vectors,
then the complete packing sequence through both finished masks. The sequence
runs at normal speed and holds on the paired masks until the next arrow-key advance.
Blue/purple identify the independent 128-bit halves. Every mask retains
its original random-draw label (`r0` through `r31`), making the reordering visible.
`pair01` and `pair23` are illustrative aliases for the nested subexpressions.
Each instruction handles both halves, traced in sequence during playback.
The expression contains two `packs_epi32` calls and one `packs_epi16`.

True remains signed -1: `FFFFFFFF` becomes `FFFF`, then `FF`. False remains zero.
The final random-draw index order is:

```text
0–3, 8–11, 16–19, 24–27 | 4–7, 12–15, 20–23, 28–31
```

Growth and fire use the same permutation, preserving the shared random draw
for both checks at each output position. State/neighbour masks retain physical
cell order. This changes draw-to-cell assignment; it does not reproduce the
unpacked random trajectory. The scene reuses S10's illustrative comparison masks.

```sh
.venv/bin/manim render -r 1920,1080 --fps 30 s11_pack_masks.py S11PackMasks
.venv/bin/python port_intro.py '/home/aryan/Downloads/COSC3500 - Milestone 2.pptx'
```

`requirements.txt` pins the versions used for these scenes. Pillow 11.3 is pinned
because Pillow 13 rejects an image allocation used by Manim 0.19's Cairo renderer.
Manim 0.22 changes
the output interface used by Manim Slides 5.7, so this environment uses 0.19.
The environment uses the bundled Python 3.12 runtime. Graphics build
dependencies were extracted locally into `.native`; no system packages were
installed. LaTeX is unnecessary because this scene uses plain text.

References: [Manim Slides quickstart](https://manim-slides.eertmans.be/latest/quickstart.html)
and [offline HTML export](https://manim-slides.eertmans.be/main/reference/sharing.html).
