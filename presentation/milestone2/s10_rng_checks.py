"""S10: four eight-float draws, each reused for growth and fire comparisons."""

import struct

from manim import (
    LEFT, RIGHT, UP, Create, FadeIn, FadeOut, LaggedStart, ManimColor, Rectangle,
    ReplacementTransform, SurroundingRectangle, Text, VGroup, Write,
)
from manim_slides import Slide

from s7_avx import BACKGROUND, BLUE, INK, MONO, MUTED, ORANGE, PALE_BLUE, SANS, TEAL
from s8_neighbours import text_at
from s9_fire_mask import cell_highlights


GROWTH = "#24633E"
FIRE = "#A83824"


def comparison_data():
    # These readable examples illustrate the operations; they are not a PCG trace.
    def float32(value):
        return struct.unpack("f", struct.pack("f", value))[0]

    p, f = float32(0.02), float32(0.01)
    batches = [list(map(float32, values)) for values in (
        (0.001, 0.030, 0.019, 0.020, 0.000, 0.500, 0.010, 0.990),
        (0.250, 0.009, 0.021, 0.015, 0.005, 0.750, 0.020, 0.011),
        (0.010, 0.002, 0.900, 0.018, 0.025, 0.000, 0.008, 0.500),
        (0.019, 0.020, 0.006, 0.400, 0.012, 0.001, 0.030, 0.009),
    )]
    growth = [[0xFFFFFFFF if value < p else 0 for value in batch] for batch in batches]
    fire = [[0xFFFFFFFF if value < f else 0 for value in batch] for batch in batches]
    return p, f, batches, growth, fire


def vector(labels, y, *, left=-6.1, width=11.8, height=0.58, size=22, masks=None, fill=PALE_BLUE):
    result = VGroup()
    for lane, label in enumerate(labels):
        true = masks is not None and bool(masks[lane])
        shade = ("#DDF3EE" if true else "#F3F5F7") if masks is not None else fill
        ink = (TEAL if true else MUTED) if masks is not None else INK
        box = Rectangle(
            width=width / 8, height=height, stroke_color="#CBD5DE", stroke_width=0.8,
            fill_color=shade, fill_opacity=1,
        )
        items = [box]
        if label:
            items.append(Text(label, font=MONO, font_size=size, color=ink))
        result.add(VGroup(*items).move_to([left + (lane + 0.5) * width / 8, y, 0]))
    return result


def label(name, target, color=INK, size=20):
    return Text(name, font=MONO, font_size=size, color=color).next_to(
        target, UP, buff=0.12
    ).align_to(target, LEFT)


def float_vector(values, y, **kwargs):
    return vector([f"{value:.3f}" for value in values], y, **kwargs)


def hex_vector(values, y):
    return vector([f"{value:08X}" for value in values], y, size=16, masks=values)


class S10RNGChecks(Slide):
    """Begin with the completed arrays, formerly HTML stage #/33."""

    def construct(self):
        self.camera.background_color = ManimColor(BACKGROUND)
        _, _, _, growth, fire = comparison_data()
        title = Text(
            "Random checks for 32 cells", font=SANS, font_size=36, color=INK
        ).to_corner(UP + LEFT, buff=0.65)
        count = text_at("4 RNG calls × 8 floats = 32 random values", -0.2, 2.5, 26, BLUE)
        reuse = text_at("Illustrative samples, shared by the p and f checks.", -0.2, 1.95, 22)
        self.add(title, count, reuse)
        for array, left, name, color in (
            (growth, -5.9, "growthChecks[4]", GROWTH),
            (fire, 0.65, "fireChecks[4]", FIRE),
        ):
            self.add(text_at(name, left + 2.625, 1.3, 23, color, mono=True))
            for i, (masks, y) in enumerate(zip(array, (0.5, -0.25, -1, -1.75))):
                self.add(text_at(f"[{i}]", left - 0.4, y, 18, mono=True))
                self.add(vector(
                    ["T" if v else "F" for v in masks], y,
                    left=left, width=5.25, height=0.46, size=20, masks=masks,
                ))
        self.add(text_at(
            "Each entry contains eight 32-bit comparison masks.", -0.2, -2.65, 23
        ))
        self.add(text_at(
            "T = FFFFFFFF       F = 00000000", -0.8, -3.2, 19, TEAL, mono=True
        ))
        self.wait(0.5)


class RNGWalkthrough(Slide):
    """Optional detailed reference scene, omitted from the final deck."""
    def construct(self):
        self.camera.background_color = ManimColor(BACKGROUND)
        p, f, batches, growth, fire = comparison_data()
        title = Text(
            "Random probability checks", font=SANS, font_size=36, color=INK
        ).to_corner(UP + LEFT, buff=0.65)
        broadcast = Text(
            "pVector = _mm256_set1_ps(static_cast<float>(p));\n"
            "fVector = _mm256_set1_ps(static_cast<float>(f));",
            font=MONO, font_size=20, color=INK, disable_ligatures=True,
            t2c={"_mm256_set1_ps": TEAL, "pVector": GROWTH, "fVector": FIRE},
        ).move_to([-0.2, 2.3, 0])
        p_row = float_vector([p] * 8, 0.95, fill="#E3F3E8")
        f_row = float_vector([f] * 8, -0.6, fill="#FCE7E3")
        p_label = label("pVector: p = 0.020", p_row, GROWTH)
        f_label = label("fVector: f = 0.010", f_row, FIRE)
        capacity = text_at("8 float32 lanes × 32 bits = 256 bits", -0.2, -2, 26)
        once = text_at("Broadcast once, before the timestep loop.", -0.2, -2.85, 22)
        self.add(title)
        self.play(Write(broadcast), run_time=1.3)
        self.play(FadeIn(p_row), FadeIn(p_label), FadeIn(f_row), FadeIn(f_label), run_time=1)
        self.play(FadeIn(capacity), FadeIn(once), run_time=0.5)
        self.wait(1)

        self.next_slide(notes="One rng.nextFloat() call gives eight 32-bit floats. These same values are compared against both probabilities.")
        rng_code = Text(
            "__m256 randoms = rng.nextFloat();   // i = 0",
            font=MONO, font_size=22, color=INK,
            t2c={"rng.nextFloat": TEAL, "randoms": BLUE},
        ).move_to(broadcast)
        randoms = float_vector(batches[0], 1.0)
        random_label = label("randoms: illustrative values in [0, 1)", randoms, BLUE)
        reuse = text_at("Use the same eight random values for both checks.", -0.2, -2.8, 23)
        self.play(
            ReplacementTransform(broadcast, rng_code), FadeOut(capacity), FadeOut(once),
            p_row.animate.set_y(-0.25), p_label.animate.shift(UP * -1.2),
            f_row.animate.set_y(-1.6), f_label.animate.shift(UP * -1),
            run_time=0.9,
        )
        self.play(FadeIn(randoms), FadeIn(random_label), FadeIn(reuse), run_time=0.8)
        self.wait(1)

        self.next_slide(notes="Compare the randoms with p using ordered less-than. The result has eight 32-bit all-one/all-zero masks; the cast preserves those bits.")
        growth_code = Text(
            "growthChecks[0] = _mm256_castps_si256(\n"
            "    _mm256_cmp_ps(randoms, pVector, _CMP_LT_OQ));",
            font=MONO, font_size=20, color=INK, disable_ligatures=True,
            t2c={"growthChecks": GROWTH, "_mm256_cmp_ps": TEAL, "_mm256_castps_si256": BLUE},
        ).move_to([-0.2, 2.35, 0])
        growth_result = hex_vector(growth[0], -1.65)
        growth_label = label("growthChecks[0]: 32-bit mask lanes (hex)", growth_result, GROWTH, 18)
        less = text_at("<", -0.2, 0.38, 28, TEAL)
        equals = text_at("=", -0.2, -0.86, 27, TEAL)
        focus = cell_highlights(randoms[3], p_row[3])
        result_focus = cell_highlights(growth_result[3])
        mask_key = text_at("FFFFFFFF = true       00000000 = false", -0.2, -2.65, 21, TEAL, mono=True)
        cast_note = text_at("The cast preserves the comparison bits.", -0.2, -3.25, 19)
        self.play(
            ReplacementTransform(rng_code, growth_code), FadeOut(f_row), FadeOut(f_label),
            FadeOut(reuse), FadeIn(less), Create(focus), run_time=0.8,
        )
        self.play(
            LaggedStart(*[FadeIn(square) for square in growth_result], lag_ratio=0.05),
            FadeIn(growth_label), FadeIn(equals), FadeIn(mask_key), FadeIn(cast_note), run_time=1.3,
        )
        self.play(Create(result_focus), run_time=0.4)
        self.wait(1.2)

        self.next_slide(notes="Store growthChecks[0]. Reuse the exact same random vector for f; no second RNG call. Equal-to-threshold values fail a strict less-than test.")
        fire_code = Text(
            "fireChecks[0] = _mm256_castps_si256(\n"
            "    _mm256_cmp_ps(randoms, fVector, _CMP_LT_OQ));",
            font=MONO, font_size=20, color=INK, disable_ligatures=True,
            t2c={"fireChecks": FIRE, "_mm256_cmp_ps": TEAL, "_mm256_castps_si256": BLUE},
        ).move_to(growth_code)
        f_row.move_to([-0.2, -0.25, 0])
        f_label = label("fVector: f = 0.010", f_row, FIRE)
        fire_result = hex_vector(fire[0], -1.65)
        fire_label = label("fireChecks[0]: 32-bit mask lanes (hex)", fire_result, FIRE, 18)
        fire_focus = cell_highlights(randoms[6], f_row[6])
        fire_result_focus = cell_highlights(fire_result[6])
        next_note = text_at("Same randoms; equality to the threshold gives false.", -0.2, -3.25, 19)
        self.play(
            ReplacementTransform(growth_code, fire_code), FadeOut(p_row), FadeOut(p_label),
            FadeOut(growth_result), FadeOut(growth_label), FadeOut(focus), FadeOut(result_focus),
            FadeIn(f_row), FadeIn(f_label), ReplacementTransform(cast_note, next_note),
            Create(fire_focus), run_time=0.9,
        )
        self.play(
            LaggedStart(*[FadeIn(square) for square in fire_result], lag_ratio=0.05),
            FadeIn(fire_label), Create(fire_result_focus), run_time=1.3,
        )
        self.wait(1.2)

        self.next_slide(notes="Each array has four vector entries. Each entry stores eight 32-bit masks. T/F below are abbreviations for FFFFFFFF/00000000.")
        self.play(*[FadeOut(mobject) for mobject in (
            fire_code, randoms, random_label, f_row, f_label, fire_result, fire_label,
            less, equals, mask_key, next_note, fire_focus, fire_result_focus,
        )], run_time=0.6)
        loop_code = text_at("for (int i = 0; i < 4; ++i)", -0.2, 2.5, 24, BLUE, mono=True)
        counter = text_at("i = 0: random results 0–7", -0.2, 2.0, 19)
        row_y = (0.45, -0.25, -0.95, -1.65)
        lefts = (-5.9, 0.65)
        names = ("growthChecks[4]", "fireChecks[4]")
        headers = VGroup(*[
            text_at(name, left + 5.25 / 2, 1.48, 23, color, mono=True)
            for name, left, color in zip(names, lefts, (GROWTH, FIRE))
        ])
        lane_labels = VGroup(*[
            text_at(str(k), left + 5.25 * (k + 0.5) / 8, 0.99, 13)
            for left in lefts for k in range(8)
        ])
        indices = VGroup(*[
            text_at(f"[{i}]", left - 0.42, y, 18, mono=True)
            for left in lefts for i, y in enumerate(row_y)
        ])
        placeholders = [
            [vector([""] * 8, y, left=left, width=5.25, height=0.46, fill="#FFFFFF")
             for y in row_y]
            for left in lefts
        ]
        stored = [
            [vector(["T" if value else "F" for value in masks], y,
                    left=left, width=5.25, height=0.46, size=20, masks=masks)
             for masks, y in zip(array, row_y)]
            for array, left in zip((growth, fire), lefts)
        ]
        bottom_randoms = float_vector(batches[0], -2.85, height=0.42, size=18)
        bottom_label = label("rng.nextFloat(): results 0–7", bottom_randoms, BLUE, 17)
        shorthand = text_at("T = FFFFFFFF (32 bits)       F = 00000000", -0.2, -3.55, 17, TEAL, mono=True)
        self.play(
            FadeIn(loop_code), FadeIn(counter), FadeIn(headers), FadeIn(lane_labels), FadeIn(indices),
            *[FadeIn(v) for array in placeholders for v in array],
            FadeIn(bottom_randoms), FadeIn(bottom_label), FadeIn(shorthand), run_time=0.9,
        )
        self.play(*[
            ReplacementTransform(placeholders[a][0], stored[a][0]) for a in range(2)
        ], run_time=0.9)
        active = VGroup(*[SurroundingRectangle(array[0], buff=0.025, color=BLUE, stroke_width=2) for array in stored])
        self.play(Create(active), run_time=0.4)
        self.wait(1)

        for i in range(1, 4):
            self.next_slide(notes=f"RNG call {i+1} supplies draw indices {i*8} through {i*8+7}; compare those same eight values with both p and f, storing array entry {i}.")
            next_counter = text_at(f"i = {i}: random results {i*8}–{i*8+7}", -0.2, 2.0, 19)
            next_randoms = float_vector(batches[i], -2.85, height=0.42, size=18)
            next_label = label(f"rng.nextFloat(): results {i*8}–{i*8+7}", next_randoms, BLUE, 17)
            self.play(
                ReplacementTransform(counter, next_counter),
                ReplacementTransform(bottom_randoms, next_randoms),
                ReplacementTransform(bottom_label, next_label), FadeOut(active), run_time=0.8,
            )
            counter, bottom_randoms, bottom_label = next_counter, next_randoms, next_label
            self.play(*[
                ReplacementTransform(placeholders[a][i], stored[a][i]) for a in range(2)
            ], run_time=0.9)
            active = VGroup(*[SurroundingRectangle(array[i], buff=0.025, color=BLUE, stroke_width=2) for array in stored])
            self.play(Create(active), run_time=0.4)
            self.wait(0.8)

        self.next_slide(notes="Four calls produce 32 random values per 32-cell batch. Both arrays hold four vectors of eight 32-bit masks. Packing into byte masks is a later step.")
        count = text_at("4 RNG calls × 8 floats = 32 random values", -0.2, 2.5, 26, BLUE)
        reuse = text_at("The same 32 values generate both sets of checks.", -0.2, 2.0, 20)
        array_size = text_at("Each array holds 4 vectors × 8 comparison masks.", -0.2, -2.55, 23)
        packing = text_at("32 bits per mask; byte packing comes next.", -0.2, -3.12, 21)
        self.play(
            ReplacementTransform(loop_code, count), ReplacementTransform(counter, reuse),
            FadeOut(active), FadeOut(bottom_randoms), FadeOut(bottom_label),
            FadeIn(array_size), FadeIn(packing), run_time=1.1,
        )
        self.wait(2)
