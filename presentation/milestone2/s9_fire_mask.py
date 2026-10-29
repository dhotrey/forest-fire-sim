"""S9: isolate the neighbour fire bit and turn it into a byte mask."""

from manim import (
    LEFT, RIGHT, UP, Create, FadeIn, FadeOut, LaggedStart, ManimColor, Rectangle,
    ReplacementTransform, SurroundingRectangle, Text, VGroup, Write,
)
from manim_slides import Slide

from s7_avx import BACKGROUND, BLUE, INK, MONO, MUTED, ORANGE, SANS, TEAL
from s8_neighbours import LANES, PURPLE, cell, example_data, text_at


def fire_detection_data():
    neighbours = example_data()[2]
    fire_vector = [2] * LANES
    fire_bits = [n & f for n, f in zip(neighbours, fire_vector)]
    mask = [0xFF if bits == f else 0x00 for bits, f in zip(fire_bits, fire_vector)]
    return neighbours, fire_vector, fire_bits, mask


def row(values, y, *, mask=False, height=0.6):
    width = 11.8 / LANES
    squares = VGroup()
    for lane, value in enumerate(values):
        if mask:
            box = Rectangle(
                width=width, height=height, stroke_color="#CBD5DE", stroke_width=0.7,
                fill_color="#DDF3EE" if value else "#F3F5F7", fill_opacity=1,
            )
            label = Text(
                f"{value:02X}", font=MONO, font_size=16,
                color=TEAL if value else MUTED,
            )
            square = VGroup(box, label)
        else:
            square = cell(value, width, height, 18)
        squares.add(square.move_to([-6.1 + width * (lane + 0.5), y, 0]))
    return squares


def row_label(name, vector, color=INK):
    return Text(name, font=MONO, font_size=21, color=color).next_to(
        vector, UP, buff=0.12
    ).align_to(vector, LEFT)


def cell_highlights(*squares, color=ORANGE):
    return VGroup(*[
        SurroundingRectangle(square, buff=0.025, color=color, stroke_width=2.5)
        for square in squares
    ])


class S9FireMask(Slide):
    def construct(self):
        self.camera.background_color = ManimColor(BACKGROUND)
        neighbours, fire_vector, fire_bits, mask_values = fire_detection_data()
        title = Text(
            "Detecting burning neighbours", font=SANS, font_size=36, color=INK
        ).to_corner(UP + LEFT, buff=0.65)
        combined = row(neighbours, 0.6, height=0.74)
        combined_label = row_label("neighbours: OR result", combined, TEAL)
        key = VGroup(*[
            text_at(label, 0, 0, 18, color)
            for label, color in (
                ("0: no bits", MUTED), ("1: tree bit", "#24633E"),
                ("2: fire bit", "#A83824"), ("3: both bits", PURPLE),
            )
        ]).arrange(RIGHT, buff=0.6).move_to([-0.2, 2.15, 0])
        caption = text_at("Keep only the fire bit: binary 10.", -0.2, -1.25, 26)
        self.add(title)
        self.play(FadeIn(combined), FadeIn(combined_label), FadeIn(key), FadeIn(caption), run_time=0.7)
        self.wait(0.25)

        broadcast_code = Text(
            "const __m256i fireVector = _mm256_set1_epi8(2);",
            font=MONO, font_size=22, color=INK, disable_ligatures=True,
            t2c={"_mm256_set1_epi8": TEAL, "fireVector": BLUE},
        ).move_to([-0.2, 2.35, 0])
        fire = row(fire_vector, -0.15)
        fire_label = row_label("fireVector", fire, BLUE)
        next_caption = text_at("_mm256_set1_epi8(2) repeats 2 in every byte.", -0.2, -2, 23)
        self.play(
            FadeOut(key), FadeOut(caption),
            combined.animate.move_to([-0.2, 1.1, 0]),
            combined_label.animate.shift(UP * 0.5),
            Write(broadcast_code), run_time=1,
        )
        self.play(
            LaggedStart(*[FadeIn(square) for square in fire], lag_ratio=0.02),
            FadeIn(fire_label), FadeIn(next_caption), run_time=1.2,
        )
        self.wait(0.25)

        and_code = Text(
            "fireBits = _mm256_and_si256(neighbours, fireVector);",
            font=MONO, font_size=21, color=INK, disable_ligatures=True,
            t2c={"_mm256_and_si256": TEAL, "fireBits": BLUE},
        ).move_to(broadcast_code)
        and_sign = text_at("AND", -0.2, 0.45, 22, TEAL)
        equals = text_at("=", -0.2, -0.8, 26, TEAL)
        bits = row(fire_bits, -1.5)
        bits_label = row_label("fireBits", bits, BLUE)
        true_lane, false_lane = 3, 0
        focus = cell_highlights(combined[true_lane], fire[true_lane])
        examples = VGroup(
            text_at("3 (11) & 2 (10) = 2 (10)", -0.2, -2.45, 23, PURPLE, mono=True),
            text_at("1 (01) & 2 (10) = 0 (00)", -0.2, -3.05, 23, MUTED, mono=True),
        )
        self.play(
            ReplacementTransform(broadcast_code, and_code), FadeOut(next_caption),
            FadeIn(and_sign), FadeIn(equals), Create(focus), run_time=0.8,
        )
        self.play(
            LaggedStart(*[FadeIn(square) for square in bits], lag_ratio=0.02),
            FadeIn(bits_label), Write(examples), run_time=1.5,
        )
        self.wait(0.4)

        self.next_slide(notes="Compare the isolated fire bits against 2.")
        compare_code = Text(
            "isPropogating =\n    _mm256_cmpeq_epi8(fireBits, fireVector);",
            font=MONO, font_size=22, color=INK, disable_ligatures=True,
            t2c={"_mm256_cmpeq_epi8": TEAL, "isPropogating": BLUE},
        ).move_to([-0.2, 2.35, 0])
        comparison = text_at("==", -0.2, 0.45, 27, TEAL)
        compare_caption = text_at("Each lane asks: is fireBits equal to 2?", -0.2, -2.35, 25)
        self.play(
            FadeOut(combined), FadeOut(combined_label), FadeOut(focus),
            FadeOut(examples), FadeOut(equals),
            ReplacementTransform(and_code, compare_code),
            ReplacementTransform(and_sign, comparison),
            bits.animate.move_to([-0.2, 1.1, 0]),
            bits_label.animate.shift(UP * 2.6),
            FadeIn(compare_caption), run_time=1.3,
        )
        self.wait(0.25)

        mask = row(mask_values, -1.5, mask=True)
        mask_label = row_label("isPropogating: byte mask (hex)", mask, TEAL)
        focus = cell_highlights(bits[true_lane], fire[true_lane])
        mask_focus = SurroundingRectangle(mask[true_lane], buff=0.025, color=ORANGE, stroke_width=2.5)
        false_focus = cell_highlights(bits[false_lane], fire[false_lane], color=BLUE)
        mask_false = SurroundingRectangle(mask[false_lane], buff=0.025, color=BLUE, stroke_width=2.5)
        comparison_examples = text_at(
            "2 == 2: FF       0 == 2: 00", -0.2, -2.65, 25, TEAL, mono=True
        )
        self.play(FadeOut(compare_caption), Create(focus), Create(false_focus), FadeIn(equals), run_time=0.6)
        self.play(
            LaggedStart(*[FadeIn(square) for square in mask], lag_ratio=0.02),
            FadeIn(mask_label), Write(comparison_examples), run_time=1.4,
        )
        self.play(Create(mask_focus), Create(mask_false), run_time=0.5)
        self.wait(0.4)

        self.play(
            FadeOut(bits), FadeOut(bits_label), FadeOut(fire), FadeOut(fire_label),
            FadeOut(compare_code), FadeOut(comparison), FadeOut(equals),
            FadeOut(focus), FadeOut(false_focus), FadeOut(mask_focus), FadeOut(mask_false),
            FadeOut(comparison_examples), FadeOut(mask_label),
            mask.animate.move_to([-0.2, 0.7, 0]), run_time=1.1,
        )
        final_label = row_label("isPropogating: neighbour-fire mask (hex)", mask, TEAL)
        true_key = text_at("FF = 0xFF = 11111111 = true", -0.2, -0.45, 25, TEAL, mono=True)
        false_key = text_at("00 = 0x00 = 00000000 = false", -0.2, -1.15, 25, MUTED, mono=True)
        conclusion = text_at("Each byte records whether that cell has a burning neighbour.", -0.2, -2.2, 22)
        self.play(FadeIn(final_label), Write(true_key), Write(false_key), FadeIn(conclusion), run_time=1.2)
        self.wait(0.5)
