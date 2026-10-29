"""S8: load four aligned neighbour vectors and combine their state bits."""

import random

from manim import (
    DOWN, LEFT, RIGHT, UP, Create, FadeIn, FadeOut, LaggedStart, ManimColor,
    Rectangle, ReplacementTransform, SurroundingRectangle, Text, TransformFromCopy,
    VGroup, Write,
)
from manim_slides import Slide

from s7_avx import BACKGROUND, BLUE, INK, MONO, MUTED, ORANGE, SANS, TEAL


PURPLE = "#70439A"
STATE_FILL = ("#F3F5F7", "#E3F3E8", "#FCE7E3", "#EEE5F6")
STATE_INK = ("#637282", "#24633E", "#A83824", PURPLE)
ROWS, COLS, LANES = 20, 36, 32
ROW, START = 10, 2


def example_data():
    rng = random.Random(56)
    grid = [[rng.randrange(3) for _ in range(COLS)] for _ in range(ROWS)]
    vectors = {
        "current": grid[ROW][START:START + LANES],
        "up": grid[ROW + 1][START:START + LANES],
        "down": grid[ROW - 1][START:START + LANES],
        "left": grid[ROW][START - 1:START + LANES - 1],
        "right": grid[ROW][START + 1:START + LANES + 1],
    }
    result = [a | b | l | r for a, b, l, r in zip(
        vectors["up"], vectors["down"], vectors["left"], vectors["right"]
    )]
    return grid, vectors, result


def cell(value, width, height, font_size):
    box = Rectangle(
        width=width, height=height, stroke_color="#CBD5DE", stroke_width=0.7,
        fill_color=STATE_FILL[value], fill_opacity=1,
    )
    digit = Text(str(value), font=MONO, font_size=font_size, color=STATE_INK[value])
    return VGroup(box, digit)


def text_at(text, x, y, size=23, color=MUTED, mono=False):
    return Text(
        text, font=MONO if mono else SANS, font_size=size, color=color,
        disable_ligatures=True,
    ).move_to([x, y, 0])


class S8Neighbours(Slide):
    def construct(self):
        self.camera.background_color = ManimColor(BACKGROUND)
        states, values, result_values = example_data()
        title = Text(
            "Finding burning neighbours", font=SANS, font_size=36, color=INK
        ).to_corner(UP + LEFT, buff=0.65)
        legend = VGroup(*[
            VGroup(
                cell(value, 0.3, 0.3, 14),
                Text(name, font=SANS, font_size=18, color=STATE_INK[value]),
            ).arrange(RIGHT, buff=0.12)
            for value, name in enumerate(("Empty", "Tree", "Fire"))
        ]).arrange(RIGHT, buff=0.42).move_to([-3.9, 2.65, 0])
        self.add(title, legend)

        # Rows increase upward on this drawing, matching main.cpp's up=idx+stride.
        focus_col = START + 16
        stencil = {
            "current": (ROW, focus_col, 0, 0),
            "up": (ROW + 1, focus_col, 0, 1),
            "down": (ROW - 1, focus_col, 0, -1),
            "left": (ROW, focus_col - 1, -1, 0),
            "right": (ROW, focus_col + 1, 1, 0),
        }
        cross = VGroup()
        for name, (r, c, x, y) in stencil.items():
            square = cell(states[r][c], 0.85, 0.85, 30).move_to([x, y - 0.2, 0])
            if name == "current":
                square[0].set_stroke(BLUE, width=3)
            cross.add(square)
        cross_labels = VGroup(
            text_at("up", 0, 1.45, 19), text_at("down", 0, -1.85, 19),
            text_at("left", -1.85, -0.2, 19), text_at("right", 1.9, -0.2, 19),
        )
        caption = text_at("Each cell reads its four immediate neighbours.", 0, -2.75)
        self.play(FadeIn(cross), FadeIn(cross_labels), FadeIn(caption), run_time=1)
        self.wait(0.3)

        self.next_slide(notes="Show the full grid and its 32-cell block.")
        side = 0.27
        prototypes = {v: cell(v, side, side, 12) for v in range(3)}
        grid_cells = [
            [prototypes[states[r][c]].copy().move_to([
                (c - (COLS - 1) / 2) * side - 0.15,
                (r - (ROWS - 1) / 2) * side - 0.55, 0,
            ]) for c in range(COLS)]
            for r in range(ROWS)
        ]
        grid = VGroup(*[square for row in grid_cells for square in row])
        current_source = VGroup(*grid_cells[ROW][START:START + LANES])
        current_outline = SurroundingRectangle(
            current_source, buff=0.015, color=BLUE, stroke_width=2.6
        )
        grid_group = VGroup(grid, current_outline)
        self.play(FadeOut(cross), FadeOut(cross_labels), FadeOut(caption), run_time=0.5)
        self.play(FadeIn(grid), run_time=1.1)
        self.play(Create(current_outline), run_time=0.6)
        grid_note = text_at("20 rows × 36 columns; the blue block contains 32 cells.", 0, -3.55, 18)
        self.play(FadeIn(grid_note), run_time=0.4)
        self.wait(0.3)

        self.play(
            grid_group.animate.scale(0.45).move_to([-4.45, -0.2, 0]),
            FadeOut(grid_note), run_time=1.1,
        )
        source_caption = text_at("current: idx", -4.45, 1.55, 18, BLUE, mono=True)
        grid_note = text_at("Illustrative grid", -4.45, -1.8, 17)
        caption = text_at("current[k] = grid[idx + k]", 0, -2.8, 22, BLUE, mono=True)
        self.play(FadeIn(source_caption), FadeIn(grid_note), FadeIn(caption), run_time=0.4)

        vector_left, vector_width = -0.55, 6.95
        vector_y = {"current": 1.5, "up": 0.55, "down": -0.2, "left": -0.95, "right": -1.7}
        vectors, labels = {}, {}
        for name in values:
            vectors[name] = VGroup(*[
                cell(value, vector_width / LANES, 0.44, 11).move_to([
                    vector_left + (lane + 0.5) * vector_width / LANES, vector_y[name], 0
                ]) for lane, value in enumerate(values[name])
            ])
            labels[name] = Text(
                name, font=MONO, font_size=18, color=BLUE if name == "current" else INK
            ).next_to(vectors[name], LEFT, buff=0.16)
        self.play(
            TransformFromCopy(current_source, vectors["current"]),
            FadeIn(labels["current"]), run_time=1.3,
        )
        self.wait(0.3)

        sources = {
            "up": VGroup(*grid_cells[ROW + 1][START:START + LANES]),
            "down": VGroup(*grid_cells[ROW - 1][START:START + LANES]),
            "left": VGroup(*grid_cells[ROW][START - 1:START + LANES - 1]),
            "right": VGroup(*grid_cells[ROW][START + 1:START + LANES + 1]),
        }
        up_down = VGroup(*[
            SurroundingRectangle(sources[name], buff=0.015, color=TEAL, stroke_width=2)
            for name in ("up", "down")
        ])
        next_source = text_at("up: idx + grid_size\ndown: idx - grid_size", -4.45, 1.6, 15, TEAL, mono=True)
        next_caption = text_at("Every lane receives the neighbour from the same column.", 0, -2.8, 22)
        self.play(
            ReplacementTransform(source_caption, next_source),
            ReplacementTransform(caption, next_caption), Create(up_down), run_time=0.7,
        )
        source_caption, caption = next_source, next_caption
        self.play(*[
            animation
            for name in ("up", "down")
            for animation in (TransformFromCopy(sources[name], vectors[name]), FadeIn(labels[name]))
        ], run_time=1.4)
        self.play(FadeOut(up_down), run_time=0.3)
        self.wait(0.3)

        for name, offset in (("left", "- 1"), ("right", "+ 1")):
            highlight = SurroundingRectangle(sources[name], buff=0.025, color=ORANGE, stroke_width=2.5)
            next_source = text_at(f"{name}: idx {offset}", -4.45, 1.6, 18, ORANGE, mono=True)
            next_caption = text_at(f"{name}[k] = grid[idx + k {offset}]", 0, -2.8, 22, ORANGE, mono=True)
            self.play(
                ReplacementTransform(source_caption, next_source),
                ReplacementTransform(caption, next_caption), Create(highlight), run_time=0.7,
            )
            source_caption, caption = next_source, next_caption
            self.play(
                TransformFromCopy(sources[name], vectors[name]), FadeIn(labels[name]), run_time=1.3,
            )
            self.play(FadeOut(highlight), run_time=0.25)
            self.wait(0.3)

        self.next_slide(notes="OR only the four neighbour vectors. The current vector is not an input to this OR.")
        code = Text(
            "neighbours =\n_mm256_or_si256(\n    _mm256_or_si256(left, right),\n    _mm256_or_si256(up, down));",
            font=MONO, font_size=18, color=INK, disable_ligatures=True,
            t2c={"_mm256_or_si256": TEAL, "neighbours": BLUE},
        ).move_to([-4.1, 1.15, 0])
        neighbour_names = ("up", "down", "left", "right")
        or_y = (1.7, 0.95, 0.2, -0.55)
        self.play(
            FadeOut(grid_group), FadeOut(grid_note), FadeOut(source_caption), FadeOut(caption),
            FadeOut(vectors["current"]), FadeOut(labels["current"]),
            *[vectors[name].animate.move_to([vector_left + vector_width / 2, y, 0])
              for name, y in zip(neighbour_names, or_y)],
            *[labels[name].animate.set_y(y) for name, y in zip(neighbour_names, or_y)],
            run_time=1,
        )
        operators = VGroup(*[
            text_at("OR", vector_left + vector_width / 2, (a + b) / 2, 15, TEAL)
            for a, b in zip(or_y, or_y[1:])
        ])
        self.play(Write(code), FadeIn(operators), run_time=1.4)
        self.wait(0.3)

        result = VGroup(*[
            cell(value, vector_width / LANES, 0.44, 11).move_to([
                vector_left + (lane + 0.5) * vector_width / LANES, -1.8, 0
            ]) for lane, value in enumerate(result_values)
        ])
        result_label = Text("OR", font=MONO, font_size=18, color=TEAL).next_to(result, LEFT, buff=0.16)
        equals = text_at("=", vector_left + vector_width / 2, -1.15, 25, TEAL)
        # Lane 3 includes both a tree and fire; it is a bit field, not a new state.
        example_lane = 3
        focus = SurroundingRectangle(
            VGroup(*[vectors[name][example_lane] for name in neighbour_names]),
            buff=0.025, color=ORANGE, stroke_width=2.5,
        )
        decimal_example = text_at("2 | 1 | 1 | 1 = 3", -4.1, -0.55, 23, PURPLE, mono=True)
        binary_example = text_at("10 | 01 | 01 | 01 = 11", -4.1, -1.25, 16, PURPLE, mono=True)
        or_caption = text_at("OR combines the bits in each matching lane.", 0, -2.75, 23)
        self.play(Create(focus), FadeIn(equals), FadeIn(result_label), run_time=0.6)
        self.play(
            LaggedStart(*[FadeIn(square) for square in result], lag_ratio=0.025),
            Write(decimal_example), Write(binary_example), FadeIn(or_caption), run_time=1.5,
        )
        result_focus = SurroundingRectangle(result[example_lane], buff=0.025, color=ORANGE, stroke_width=2.5)
        self.play(Create(result_focus), run_time=0.4)
        self.wait(0.5)

        self.next_slide(notes="Inspect the combined bits before extracting the fire bit.")
        self.play(
            FadeOut(code), FadeOut(operators), FadeOut(equals), FadeOut(focus),
            FadeOut(result_focus), FadeOut(decimal_example), FadeOut(binary_example),
            FadeOut(or_caption), FadeOut(result_label),
            *[FadeOut(vectors[name]) for name in neighbour_names],
            *[FadeOut(labels[name]) for name in neighbour_names],
            result.animate.scale_to_fit_width(11.8).move_to([-0.2, 0.6, 0]),
            run_time=1.2,
        )
        final_label = Text(
            "neighbours: bitwise OR result", font=SANS, font_size=24, color=TEAL
        ).next_to(result, UP, buff=0.25).align_to(result, LEFT)
        combined_bits = text_at("1 (01) | 2 (10) = 3 (11)", -0.2, -0.65, 28, PURPLE, mono=True)
        explanation = text_at("3 preserves both the tree bit and the fire bit.", -0.2, -1.45, 24)
        next_step = text_at("The fire bit is isolated in the next check.", -0.2, -2.35, 22)
        result_key = VGroup(*[
            text_at(label, 0, 0, 18, STATE_INK[v])
            for v, label in enumerate(("0: no bits", "1: tree bit", "2: fire bit", "3: both bits"))
        ]).arrange(RIGHT, buff=0.65).move_to([-0.2, 1.85, 0])
        self.play(
            FadeOut(legend), FadeIn(result_key), FadeIn(final_label),
            Write(combined_bits), FadeIn(explanation), FadeIn(next_step), run_time=1.2,
        )
        self.wait(0.5)
