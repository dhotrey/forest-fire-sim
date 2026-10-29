"""S11: trace signed AVX2 packing independently inside each 128-bit half."""

from manim import (
    LEFT, UP, Create, DashedLine, FadeIn, FadeOut, LaggedStart, ManimColor,
    Rectangle, ReplacementTransform, SurroundingRectangle, Text, TransformFromCopy,
    VGroup, Write,
)
from manim_slides import Slide

from s7_avx import BACKGROUND, BLUE, INK, MONO, MUTED, ORANGE, SANS, TEAL
from s8_neighbours import PURPLE, text_at
from s9_fire_mask import cell_highlights
from s10_rng_checks import FIRE, GROWTH, comparison_data


def pack_draw_ids(a, b, source_bits):
    half = 128 // source_bits
    return a[:half] + b[:half] + a[half:] + b[half:]


def packing_data():
    _, _, _, growth, fire = comparison_data()
    inputs = [list(range(i * 8, (i + 1) * 8)) for i in range(4)]
    pairs = [pack_draw_ids(inputs[i], inputs[i + 1], 32) for i in (0, 2)]
    order = pack_draw_ids(pairs[0], pairs[1], 16)
    return inputs, pairs, order, sum(growth, []), sum(fire, [])


def mask_row(draw_ids, masks, bits, y):
    width = 11.8 / len(draw_ids)
    result = VGroup()
    for position, draw_id in enumerate(draw_ids):
        left_half = draw_id % 8 < 4
        box = Rectangle(
            width=width, height=0.62, stroke_color="#CBD5DE", stroke_width=0.8,
            fill_color="#EAF1FC" if left_half else "#EEE5F6", fill_opacity=1,
        )
        draw = Text(
            f"r{draw_id}", font=MONO, font_size=11, color=BLUE if left_half else PURPLE
        ).move_to([0, 0.16, 0])
        value = (1 << bits) - 1 if masks[draw_id] else 0
        digit = Text(
            f"{value:0{bits // 4}X}", font=MONO, font_size=14,
            color=TEAL if value else MUTED,
        ).move_to([0, -0.1, 0])
        result.add(VGroup(box, draw, digit).move_to([
            -6.1 + (position + 0.5) * width, y, 0
        ]))
    return result


def row_label(name, target, color=INK, size=18):
    return Text(name, font=MONO, font_size=size, color=color).next_to(
        target, UP, buff=0.12
    ).align_to(target, LEFT)


def code(text, y=2.35, size=18):
    return Text(
        text, font=MONO, font_size=size, color=INK, disable_ligatures=True,
        t2c={"_mm256_packs_epi32": TEAL, "_mm256_packs_epi16": ORANGE,
             "isGrowing": GROWTH, "isBurning": FIRE},
    ).move_to([-0.2, y, 0])


def empty_frame(target):
    return VGroup(*[square[0].copy().set_fill(opacity=0.35) for square in target])


class S11PackMasks(Slide):
    def transfer(self, sources, target, draw_ids, positions):
        self.play(LaggedStart(*[
            TransformFromCopy(sources[draw_ids[i]], target[i]) for i in positions
        ], lag_ratio=0.035), run_time=1.0)

    def construct(self):
        self.camera.background_color = ManimColor(BACKGROUND)
        inputs, pair_ids, order, growth, fire = packing_data()
        title = Text(
            "Packing comparison masks", font=SANS, font_size=36, color=INK
        ).to_corner(UP + LEFT, buff=0.65)
        full_code = code(
            "__m256i isGrowing = _mm256_packs_epi16(\n"
            "    _mm256_packs_epi32(growthChecks[0], growthChecks[1]),\n"
            "    _mm256_packs_epi32(growthChecks[2], growthChecks[3]));", y=2.3,
        )
        sources = [mask_row(ids, growth, 32, y) for ids, y in zip(inputs, (1, 0, -1, -2))]
        source_labels = [row_label(f"growthChecks[{i}]", v, GROWTH, 17) for i, v in enumerate(sources)]
        source_by_draw = {draw: square for ids, v in zip(inputs, sources) for draw, square in zip(ids, v)}
        divider = DashedLine([-0.2, 1.7, 0], [-0.2, -2.15, 0], dash_length=0.08, color=MUTED, stroke_width=1)
        half_key = VGroup(
            text_at("Left 128-bit half", -3.15, -2.85, 21, BLUE),
            text_at("Right 128-bit half", 2.75, -2.85, 21, PURPLE),
        )
        hint = text_at("r = random draw index; hexadecimal mask underneath.", -0.2, -3.45, 19)
        self.add(title, divider)
        self.play(Write(full_code), run_time=1.3)
        self.play(*[FadeIn(m) for m in sources + source_labels], FadeIn(half_key), FadeIn(hint), run_time=1)
        self.wait(0.25)

        self.next_slide(notes="Pack the first pair of inputs within the left half.")
        first_code = code("pair01 = _mm256_packs_epi32(growthChecks[0], growthChecks[1]);")
        pair01 = mask_row(pair_ids[0], growth, 16, -1.7)
        frame01 = empty_frame(pair01)
        pair01_label = row_label("pair01: 16 × 16-bit masks", pair01, TEAL, 17)
        caption = text_at("One packs_epi32, shown first in the left half.", -0.2, -2.65, 23)
        signed_note = text_at("Signed -1: FFFFFFFF becomes FFFF. Zero stays zero.", -0.2, -3.3, 19)
        self.play(
            ReplacementTransform(full_code, first_code), FadeOut(sources[2]), FadeOut(sources[3]),
            FadeOut(source_labels[2]), FadeOut(source_labels[3]), FadeOut(hint),
            sources[1].animate.set_y(-0.2), source_labels[1].animate.shift(UP * -0.2),
            half_key.animate.shift(UP * 5.6), run_time=0.9,
        )
        self.play(FadeIn(frame01), FadeIn(pair01_label), FadeIn(caption), FadeIn(signed_note), run_time=0.5)
        self.transfer(source_by_draw, pair01, pair_ids[0], range(8))
        self.wait(0.25)

        next_caption = text_at("The same instruction also packs the right half.", -0.2, -2.65, 23)
        self.play(ReplacementTransform(caption, next_caption), run_time=0.5)
        caption = next_caption
        self.transfer(source_by_draw, pair01, pair_ids[0], range(8, 16))
        self.remove(frame01, *pair01.submobjects)
        self.add(pair01)
        self.wait(0.25)

        second_code = code("pair23 = _mm256_packs_epi32(growthChecks[2], growthChecks[3]);")
        sources[2].move_to([-0.2, 1, 0])
        sources[3].move_to([-0.2, -0.2, 0])
        labels23 = [row_label(f"growthChecks[{i}]", sources[i], GROWTH, 17) for i in (2, 3)]
        pair23 = mask_row(pair_ids[1], growth, 16, -1.7)
        frame23 = empty_frame(pair23)
        pair23_label = row_label("pair23: 16 × 16-bit masks", pair23, TEAL, 17)
        next_caption = text_at("Pack the second pair in the same two halves.", -0.2, -2.65, 23)
        self.play(
            FadeOut(sources[0]), FadeOut(sources[1]), FadeOut(source_labels[0]), FadeOut(source_labels[1]),
            FadeOut(pair01), FadeOut(pair01_label), ReplacementTransform(first_code, second_code),
            ReplacementTransform(caption, next_caption),
            FadeIn(sources[2]), FadeIn(sources[3]), *[FadeIn(m) for m in labels23],
            FadeIn(frame23), FadeIn(pair23_label), run_time=0.9,
        )
        caption = next_caption
        self.transfer(source_by_draw, pair23, pair_ids[1], range(16))
        self.remove(frame23, *pair23.submobjects)
        self.add(pair23)
        self.wait(0.25)

        final_code = code("isGrowing = _mm256_packs_epi16(pair01, pair23);", size=21)
        pair01.move_to([-0.2, 1, 0])
        self.play(
            FadeOut(sources[2]), FadeOut(sources[3]), *[FadeOut(m) for m in labels23],
            FadeOut(pair23_label), FadeIn(pair01), pair23.animate.set_y(-0.2),
            ReplacementTransform(second_code, final_code), run_time=0.9,
        )
        pair_labels = [row_label(name, v, TEAL, 17) for name, v in (
            ("pair01: 16 × 16-bit masks", pair01), ("pair23: 16 × 16-bit masks", pair23)
        )]
        packed = mask_row(order, growth, 8, -1.7)
        packed_frame = empty_frame(packed)
        packed_label = row_label("isGrowing: 32 × 8-bit masks", packed, GROWTH, 17)
        intermediate_by_draw = {draw: square for ids, v in zip(pair_ids, (pair01, pair23)) for draw, square in zip(ids, v)}
        next_caption = text_at("One packs_epi16, shown first in the left half.", -0.2, -2.65, 23)
        next_note = text_at("FFFF becomes FF; 0000 becomes 00.", -0.2, -3.3, 21)
        self.play(
            *[FadeIn(m) for m in pair_labels], FadeIn(packed_frame), FadeIn(packed_label),
            ReplacementTransform(caption, next_caption), ReplacementTransform(signed_note, next_note), run_time=0.5,
        )
        caption, signed_note = next_caption, next_note
        self.transfer(intermediate_by_draw, packed, order, range(16))
        self.wait(0.25)

        next_caption = text_at("Both halves together form one 256-bit result.", -0.2, -2.65, 23)
        self.play(ReplacementTransform(caption, next_caption), run_time=0.5)
        caption = next_caption
        self.transfer(intermediate_by_draw, packed, order, range(16, 32))
        self.remove(packed_frame, *packed.submobjects)
        self.add(packed)
        self.wait(0.25)

        self.play(
            FadeOut(pair01), FadeOut(pair23), *[FadeOut(m) for m in pair_labels],
            FadeOut(final_code), FadeOut(divider), FadeOut(half_key), FadeOut(caption),
            FadeOut(signed_note), FadeOut(packed_label), packed.animate.set_y(0.8), run_time=1,
        )
        packed_label = row_label("isGrowing: 32 byte masks", packed, GROWTH)
        count = text_at("Two 32→16 packs, then one 16→8 pack", -0.2, 2.3, 27)
        lane_indices = VGroup(*[
            text_at(str(i), square.get_center()[0], 0.17, 11) for i, square in enumerate(packed)
        ])
        lane_word = text_at("lane", -6.55, 0.17, 12)
        mapping = text_at("Output lane 4 now uses random draw 8.", -0.2, -0.65, 25, BLUE)
        preservation = text_at("FFFFFFFF → FFFF → FF   (signed -1 throughout)", -0.2, -1.5, 22, TEAL, mono=True)
        reordering = text_at("Mask bits are preserved; the draw order changes.", -0.2, -2.4, 23)
        focus = cell_highlights(packed[4])
        self.play(
            FadeIn(packed_label), FadeIn(count), FadeIn(lane_indices), FadeIn(lane_word),
            FadeIn(mapping), Write(preservation), FadeIn(reordering), Create(focus), run_time=1.2,
        )
        self.wait(0.4)

        fire_code = code(
            "__m256i isBurning = _mm256_packs_epi16(\n"
            "    _mm256_packs_epi32(fireChecks[0], fireChecks[1]),\n"
            "    _mm256_packs_epi32(fireChecks[2], fireChecks[3]));", y=2.3,
        )
        self.play(
            FadeOut(count), FadeOut(lane_indices), FadeOut(lane_word), FadeOut(mapping),
            FadeOut(preservation), FadeOut(reordering), FadeOut(focus),
            packed.animate.set_y(0.95), packed_label.animate.shift(UP * 0.15), Write(fire_code), run_time=1.1,
        )
        fire_packed = mask_row(order, fire, 8, -0.9)
        fire_label = row_label("isBurning: 32 byte masks", fire_packed, FIRE)
        same_order = text_at("Both masks use the identical draw-index order.", -0.2, -2.0, 24)
        byte_key = text_at("True: FF       False: 00", -0.2, -2.95, 23, TEAL, mono=True)
        self.play(
            LaggedStart(*[FadeIn(square) for square in fire_packed], lag_ratio=0.015),
            FadeIn(fire_label), FadeIn(same_order), FadeIn(byte_key), run_time=1.2,
        )
        self.wait(0.35)

        paired = text_at("The growth and fire checks stay paired.", -0.2, 2.35, 27)
        example = text_at("Lane 8 uses draw 16 for both p and f.", -0.2, -2.0, 24, BLUE)
        state_order = text_at("State and neighbour masks keep their original cell order.", -0.2, -2.8, 21)
        pair_focus = cell_highlights(packed[8], fire_packed[8])
        self.play(
            ReplacementTransform(fire_code, paired), ReplacementTransform(same_order, example),
            FadeOut(byte_key), FadeIn(state_order), Create(pair_focus), run_time=1,
        )
        self.wait(0.5)
