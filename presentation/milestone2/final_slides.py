"""Milestone 2 methodology, rule masks, blending and closing slides."""

from pathlib import Path

from manim import (
    DOWN, LEFT, RIGHT, UP, Create, FadeIn, FadeOut, ImageMobject,
    ManimColor, Rectangle, ReplacementTransform, SurroundingRectangle,
    Text, VGroup,
)
from manim_slides import Slide

from s7_avx import BACKGROUND, BLUE, INK, MONO, MUTED, ORANGE, SANS, TEAL
from s8_neighbours import STATE_FILL, STATE_INK, example_data, text_at
from s10_rng_checks import FIRE, GROWTH
from s11_pack_masks import packing_data


ROOT = Path(__file__).resolve().parent


def heading(scene, title):
    scene.camera.background_color = ManimColor(BACKGROUND)
    obj = Text(title, font=SANS, font_size=36, color=INK)
    if obj.width > 12.6:
        obj.scale_to_fit_width(12.6)
    obj.to_corner(UP + LEFT, buff=0.65)
    scene.add(obj)
    return obj


def fitted(text, x, y, size=23, color=MUTED, width=12, mono=False):
    obj = text_at(text, x, y, size, color, mono=mono)
    if obj.width > width:
        obj.scale_to_fit_width(width)
    return obj


def code_lines(lines, x, top, size=18, width=12, spacing=0.1):
    rows = VGroup(*[
        Text(line.lstrip() or " ", font=MONO, font_size=size, color=INK,
             disable_ligatures=True) for line in lines
    ]).arrange(DOWN, aligned_edge=LEFT, buff=spacing)
    char_width = Text("M", font=MONO, font_size=size).width
    for row, line in zip(rows, lines):
        row.shift(RIGHT * (len(line) - len(line.lstrip())) * char_width)
    if rows.width > width:
        rows.scale_to_fit_width(width)
    rows.move_to([x, top, 0], aligned_edge=UP + LEFT)
    return rows


def byte_row(values, y, mask=False):
    result = VGroup()
    width = 10.6 / 32
    for i, value in enumerate(values):
        fill = ("#DDF3EE" if value else "#F3F5F7") if mask else STATE_FILL[value]
        ink = (TEAL if value else MUTED) if mask else STATE_INK[value]
        box = Rectangle(width=width, height=0.44, stroke_color="#CBD5DE",
                        stroke_width=0.7, fill_color=fill, fill_opacity=1)
        label = Text("FF" if value else "00", font=MONO, font_size=11, color=ink) if mask else Text(
            str(value), font=MONO, font_size=16, color=ink)
        result.add(VGroup(box, label).move_to([-6 + (i + 0.5) * width, y, 0]))
    return result


def row_name(name, row, color=INK):
    return Text(name, font=MONO, font_size=16, color=color).next_to(
        row, UP, buff=0.08).align_to(row, LEFT)


def rule_data():
    _, vectors, neighbours = example_data()
    _, _, order, growth, fire = packing_data()
    current = vectors["current"]
    growing = [v == 0 and bool(growth[r]) for v, r in zip(current, order)]
    burning = [v == 1 and (bool(fire[r]) or bool(n & 2))
               for v, r, n in zip(current, order, neighbours)]
    empty = [v == 2 for v in current]
    return current, growing, burning, empty


class S3Methodology(Slide):
    def construct(self):
        heading(self, "Benchmarking methodology")
        statements = (
            "Version tags in git", "-O3 -march=native",
            "8320 × 8320 cells, 500 timesteps", "Five runs per configuration",
            "Minimum runtime; range shown", "Fixed seeds per configuration",
        )
        left = VGroup(*[
            Text(s, font=SANS, font_size=21, color=INK)
            for s in statements
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.32)
        left.move_to([-6.1, 1.8, 0], aligned_edge=UP + LEFT)
        node = ImageMobject(str(ROOT / "assets/intro/node-info.png"))
        node.scale_to_fit_height(4.9).move_to([2.45, 0.1, 0])
        self.add(left, node)
        self.wait(0.5)
        self.next_slide(notes="Transition to the binary's build information.")
        build = ImageMobject(str(ROOT / "assets/intro/build-info.png"))
        build.scale_to_fit_height(4.9).move_to([2.45, 0.1, 0])
        context = fitted("Version, compiler and build flags stay with each run.",
                         -1.2, -3.05, 22, width=10)
        self.play(FadeOut(node), FadeIn(build), FadeIn(context), run_time=0.9)
        self.wait(0.5)


class S9RuleMasks(Slide):
    def construct(self):
        heading(self, "Simulation rule masks")
        _, growing, burning, empty = rule_data()
        for y, name, rule, values, color in (
            (1.15, "treeGrowing",
             "An empty cell grows a tree when its growth check passes.", growing, GROWTH),
            (-0.65, "treeBurning",
             "An existing tree burns if its ignition check passes or a neighbour is burning.", burning, FIRE),
            (-2.45, "isToBeEmpty",
             "A currently burning cell becomes empty on the next timestep.", empty, ORANGE),
        ):
            label = Text(name, font=MONO, font_size=23, color=color)
            label.move_to([-6, y + 1, 0], aligned_edge=LEFT)
            explanation = Text(rule, font=SANS, font_size=21, color=INK)
            if explanation.width > 12:
                explanation.scale_to_fit_width(12)
            explanation.move_to([-6, y + 0.5, 0], aligned_edge=LEFT)
            self.add(label, explanation, byte_row(values, y, mask=True))
        self.wait(0.5)


class S10Blending(Slide):
    def construct(self):
        heading(self, "Blending the next state")
        lines = code_lines([
            "nextVector = _mm256_blendv_epi8(nextVector, treeVector, treeGrowing);",
            "nextVector = _mm256_blendv_epi8(nextVector, fireVector, treeBurning);",
            "nextVector = _mm256_blendv_epi8(nextVector, emptyVector, isToBeEmpty);",
        ], -6, 1.85, size=21, width=12, spacing=0.45)
        self.add(lines, fitted(
            "FF selects the replacement byte; 00 keeps the existing byte.",
            -0.7, -1.6, 23, TEAL, width=11.5,
        ))
        self.wait(0.5)


def chart(scene, title, filename, annotation):
    heading(scene, title)
    plot = ImageMobject(str(ROOT.parent.parent / "plots/benchmarks" / filename))
    plot.scale_to_fit_height(5.65).move_to([-0.65, -0.05, 0])
    scene.add(plot, fitted(annotation, -1.1, -3.18, 23, BLUE, width=10.5))
    scene.wait(0.5)


class S11AVXResults(Slide):
    def construct(self):
        chart(self, "AVX results", "benchmark-serial-v-avx.png",
              "85.35 s saved     72.5% less runtime     3.63× speedup")


class S12OpenMP(Slide):
    def construct(self):
        heading(self, "OpenMP: rows shared across a persistent thread team")
        lines = code_lines([
            "#pragma omp parallel shared(grid, next)",
            "{",
            "  // Per-thread seeds and streams",
            "  pcg32_8 rng(seeds, streams);",
            "  for (int t = 0; t < timesteps; ++t) {",
            "    #pragma omp for schedule(static)",
            "    for (int x = 1; x < grid_size - 1; ++x) {",
            "      // AVX row updates",
            "    } // Implicit barrier",
            "    #pragma omp single",
            "    { std::swap(grid, next); }",
            "    // Implicit barrier",
            "  }",
            "}",
        ], -6.1, 2.65, size=17, width=7.4, spacing=0.11)
        self.add(lines)
        paragraphs = [
            ("Shared buffers", "Read current grid.\nWrite separate rows of next.", BLUE),
            ("Private mutable state", "One RNG per thread.\nTemporary vectors stay local.", TEAL),
            ("Synchronise each timestep", "Finish every row.\nSwap once using single.\nWait before the next step.", ORANGE),
        ]
        for y, (title, body, color) in zip((2.05, 0.55, -1.15), paragraphs):
            label = Text(title, font=SANS, font_size=23, color=color)
            label.move_to([1.7, y, 0], aligned_edge=LEFT)
            explanation = Text(body, font=SANS, font_size=20, color=MUTED, line_spacing=0.8)
            explanation.next_to(label, DOWN, buff=0.18).align_to(label, LEFT)
            self.add(label, explanation)
        focus = SurroundingRectangle(lines[0], color=BLUE, buff=0.05)
        self.play(Create(focus), run_time=0.5)
        self.wait(0.3)
        for indices, color, note in (
            ((2, 3), TEAL, "Each thread owns its mutable RNG."),
            ((5, 6, 7, 8), BLUE, "Static row ownership; finish all writes before swapping."),
            ((9, 10, 11), ORANGE, "One swap and an implicit barrier before the next timestep."),
        ):
            self.next_slide(notes=note)
            next_focus = SurroundingRectangle(VGroup(*[lines[i] for i in indices]), color=color, buff=0.05)
            self.play(ReplacementTransform(focus, next_focus), run_time=0.6)
            focus = next_focus
            self.wait(0.3)


class S13Scaling(Slide):
    def construct(self):
        chart(self, "OpenMP scaling for a fixed workload", "benchmark-omp-scaling.png",
              "4 to 8 threads: 1.97×     Ideal 3.96 s; observed 4.02 s")
        self.next_slide(notes="Amdahl's law limits speedup through the serial fraction.")
        plot = self.mobjects[1]
        self.play(plot.animate.scale(0.83).shift(UP * 0.35),
                  FadeOut(self.mobjects[2]), run_time=0.65)
        self.add(fitted("S(N) = 1 / (s + (1 − s) / N)", -2.6, -2.65, 25, BLUE, width=7))
        self.add(fitted("s: serial fraction of one-thread runtime; N: threads", -1.3, -3.2, 20, width=10))
        self.wait(0.5)


class S14Combined(Slide):
    def construct(self):
        chart(self, "Combined AVX and OpenMP results", "benchmark-final-comparison-8-threads.png",
              "117.77 s to 4.02 s     29.3× overall speedup")


class S15Reflection(Slide):
    def construct(self):
        title = heading(self, "Correctness and reflection")
        rows = VGroup()
        for y, name, detail, color in (
            (2.0, "Serial", "One RNG stream", BLUE),
            (0.95, "AVX", "Eight SIMD RNG streams", TEAL),
            (-0.1, "OpenMP", "Eight streams per thread; different seeds per thread", ORANGE),
        ):
            label = Text(name, font=SANS, font_size=27, color=color)
            label.move_to([-5.9, y, 0], aligned_edge=LEFT)
            body = fitted(detail, 1.3, y, 24, INK, width=8.2)
            rows.add(label, body)
        checked = fitted("Checked the implementation against the cell-update rules.",
                         -0.3, -1.4, 25, TEAL)
        qualification = fitted("A direct scalar check requires matched random inputs per cell and timestep.",
                               -0.7, -2.2, 20, width=11.4)
        trajectory = fitted("Different random trajectories; the same intended update rules.",
                            -0.7, -2.95, 21, width=11)
        self.add(rows, checked, qualification, trajectory)
        self.wait(0.5)
        self.next_slide(notes="AVX and OpenMP reduce this workload from nearly 118 seconds to four seconds.")
        self.play(*[FadeOut(m) for m in (rows, checked, qualification, trajectory)],
                  ReplacementTransform(title, Text(
                      "Conclusion", font=SANS, font_size=36, color=INK
                  ).to_corner(UP + LEFT, buff=0.65)), run_time=0.7)
        self.add(fitted("117.77 s  →  4.02 s", -0.5, 1.0, 54, BLUE))
        self.add(fitted("29.3× overall speedup", -0.5, -0.25, 36, TEAL))
        self.add(fitted("AVX: 32 cells together     OpenMP: rows across cores", -0.5, -1.6, 24))
        self.add(fitted("Thank you", -0.5, -2.55, 27, INK))
        self.wait(0.5)


class S16AIDisclosure(Slide):
    def construct(self):
        heading(self, "AI Disclosure")
        intro = Text(
            "AI models, including ChatGPT 6.1-sol, helped me produce\n"
            "this assignment and presentation. I used AI tools to:",
            font=SANS, font_size=24, color=INK, line_spacing=0.9,
        )
        if intro.width > 12:
            intro.scale_to_fit_width(12)
        intro.move_to([-6.05, 2.25, 0], aligned_edge=UP + LEFT)
        self.add(intro)
        uses = (
            "Create scripts to visualise the simulation and benchmarks.",
            "Write the program that generated the presentation animations.",
            "Understand and analyse the benchmark data.",
            "Write Slurm scripts to submit jobs.",
            "Polish my presentation script.",
        )
        for i, text in enumerate(uses):
            y = 0.65 - i * 0.8
            bullet = Text("•", font=SANS, font_size=25, color=BLUE).move_to([-6, y, 0])
            body = Text(text, font=SANS, font_size=23, color=INK)
            body.move_to([-5.65, y, 0], aligned_edge=LEFT)
            self.add(bullet, body)
        self.wait(0.5)


class S17Bibliography(Slide):
    def construct(self):
        heading(self, "Bibliography")
        entries = (
            ("1. Drossel & Schwabl (1992). Self-organized critical forest-fire model.",
             "doi.org/10.1103/PhysRevLett.69.1629"),
            ("2. Wenzel Jakob. PCG32 and the AVX2 pcg32_8 implementation.",
             "github.com/wjakob/pcg32"),
            ("3. LLVM Project. AVX2 intrinsics reference.",
             "clang.llvm.org/doxygen/avx2intrin_8h.html"),
            ("4. OpenMP ARB. Work-distribution constructs and single.",
             "openmp.org/spec-html/5.2/openmpch11.html; openmpse62.html"),
            ("5. LLNL. Introduction to Parallel Computing Tutorial. Amdahl's law.",
             "hpc.llnl.gov/documentation/tutorials/introduction-parallel-computing-tutorial"),
            ("6. Sergey Slotin. Algorithms for Modern Hardware: Masking and Blending.",
             "en.algorithmica.org/hpc/simd/masking/"),
            ("7. The Manim Community Developers. Manim Community v0.19.0.",
             "docs.manim.community/en/v0.19.0/"),
        )
        for i, (description, url) in enumerate(entries):
            y = 2.45 - i * 0.78
            label = Text(description, font=SANS, font_size=21, color=INK)
            label.move_to([-6.05, y, 0], aligned_edge=LEFT)
            link = Text(url, font=MONO, font_size=16, color=BLUE)
            if link.width > 11.6:
                link.scale_to_fit_width(11.6)
            link.next_to(label, DOWN, buff=0.1).align_to(label, LEFT)
            self.add(label, link)
        self.wait(0.5)
