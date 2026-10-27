# Milestone 2 animations

## Full presentation

Open `milestone2.html` for PowerPoint slides 1–6 followed by the four S7 animation
stages. Use the arrow keys to move between slides. Slide 2 preserves the original
embedded forest-fire GIF and its looping animation.

The imported slides preserve their PowerPoint layouts as rendered images. Edit
the original PowerPoint, then run the import again to refresh them:

```sh
.venv/bin/python port_intro.py '/home/aryan/Downloads/COSC3500 - Milestone 2.pptx'
```

The source PowerPoint and S7 animation are separate from the generated full deck.
The full HTML includes all its media and works offline.

## S7

Open `s7.html` in a browser. Use the right arrow to advance and the left arrow
to go back. Space pauses or resumes the current animation. Each animation
finishes and holds until you advance.
The HTML includes its videos and presentation assets, so it works offline.

The four stages follow the S7 notes in `script-m2.md`:

1. Write the load instruction and show a 256-bit register.
2. Divide it into eight 32-bit integer lanes.
3. Reveal the one-byte `CellState` type.
4. Subdivide the same register into 32 byte lanes, numbered 0 to 31.

The lane numbers indicate positions, not cell-state values. The load copies
32 bytes; this scene does not claim a 32-times speedup or show state updates.
The layout uses a white background and leaves the bottom-right corner clear
for the face recording.

`s7-preview.mp4` plays all four stages consecutively for a quick review.
Use the interactive HTML when recording narration at your own pace.

## Render again

Run these commands from this directory, using the existing local environment:

```sh
.venv/bin/manim render -r 1920,1080 --fps 30 s7_avx.py S7AVX
cp media/videos/s7_avx/1080p30/S7AVX.mp4 s7-preview.mp4
XDG_CACHE_HOME="$PWD/.cache" .venv/bin/manim-slides convert S7AVX s7.html --one-file --offline -creveal_theme=white -cbackground_color=white -ccontrols=true -cmargin=0
```

`requirements.txt` pins the versions used for this scene. Manim 0.22 changes
the output interface used by Manim Slides 5.7, so this environment uses 0.19.
The environment uses the bundled Python 3.12 runtime. Graphics build
dependencies were extracted locally into `.native`; no system packages were
installed. LaTeX is unnecessary because this scene uses plain text.

References: [Manim Slides quickstart](https://manim-slides.eertmans.be/latest/quickstart.html)
and [offline HTML export](https://manim-slides.eertmans.be/main/reference/sharing.html).
