"""S7: a 256-bit load directly divided into thirty-two one-byte cells."""

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Create,
    FadeIn,
    FadeOut,
    LaggedStart,
    Line,
    ManimColor,
    Rectangle,
    ReplacementTransform,
    Text,
    VGroup,
    Write,
)
from manim_slides import Slide


BACKGROUND = "#FFFFFF"
INK = "#172B4D"
MUTED = "#526171"
BLUE = "#2258B5"
PALE_BLUE = "#EAF1FC"
TEAL = "#087F76"
PALE_TEAL = "#E0F3EE"
ORANGE = "#A44912"
MONO = "Noto Sans Mono"
SANS = "DejaVu Sans"


class S7AVX(Slide):
    def construct(self):
        self.camera.background_color = ManimColor(BACKGROUND)

        title = Text(
            "Loading cell states with AVX2", font=SANS, font_size=36, color=INK
        ).to_corner(UP + LEFT, buff=0.65)
        code = VGroup(
            *[
                Text(
                    line,
                    font=MONO,
                    font_size=25,
                    color=INK,
                    disable_ligatures=True,
                    t2c={"__m256i": BLUE, "_mm256_loadu_si256": TEAL},
                )
                for line in (
                    "__m256i current = _mm256_loadu_si256(",
                    "    reinterpret_cast<const __m256i *>(",
                    "        grid.data() + idx));",
                )
            ]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        code.move_to([-0.7, 1.8, 0])

        # The rectangle keeps exactly the same width as its lanes are subdivided.
        register = Rectangle(
            width=11.8,
            height=0.9,
            stroke_color=BLUE,
            stroke_width=2.5,
            fill_color=PALE_BLUE,
            fill_opacity=1,
        ).move_to([-0.35, -0.3, 0])
        register_label = Text(
            "current: 256-bit register", font=SANS, font_size=22, color=MUTED
        ).next_to(register, UP, buff=0.2).align_to(register, LEFT)
        capacity = Text(
            "256 bits", font=SANS, font_size=30, color=BLUE
        ).move_to(register)
        equation = Text(
            "256 bits = 32 bytes", font=SANS, font_size=32, color=INK
        ).move_to([-0.35, -1.35, 0])
        caption = Text(
            "One load reads 32 consecutive bytes from grid[idx].",
            font=SANS,
            font_size=23,
            color=MUTED,
        ).move_to([-0.35, -2.15, 0])

        self.add(title)
        self.play(Write(code), run_time=2.2)
        self.play(Create(register), FadeIn(register_label), run_time=0.8)
        self.play(FadeIn(capacity), FadeIn(equation), FadeIn(caption), run_time=0.7)
        self.wait(1.5)

        self.next_slide(notes="Our CellState type uses an 8-bit integer: one byte per cell.")
        cell_type = Text(
            "enum class CellState : std::uint8_t { Empty, Tree, Burning };",
            font=MONO,
            font_size=23,
            color=INK,
            disable_ligatures=True,
            t2c={"std::uint8_t": ORANGE, "CellState": TEAL},
        )
        if cell_type.width > 12.0:
            cell_type.scale_to_fit_width(12.0)
        cell_type.move_to([-0.35, 1.8, 0])
        cell_size = Text(
            "1 cell = 8 bits = 1 byte", font=SANS, font_size=32, color=ORANGE
        ).move_to(equation)
        byte_caption = Text(
            "Our cell state uses an 8-bit unsigned integer.",
            font=SANS,
            font_size=23,
            color=MUTED,
        ).move_to(caption)
        self.play(FadeOut(code), run_time=0.35)
        self.play(
            FadeOut(capacity),
            Write(cell_type),
            ReplacementTransform(equation, cell_size),
            ReplacementTransform(caption, byte_caption),
            run_time=1.3,
        )
        self.wait(1.5)

        byte_dividers = VGroup(
            *[
                Line(
                    register.get_left() + RIGHT * register.width * i / 32 + DOWN * 0.45,
                    register.get_left() + RIGHT * register.width * i / 32 + UP * 0.45,
                    color=TEAL,
                    stroke_width=1.2,
                )
                for i in range(1, 32)
            ]
        )
        cell_labels = VGroup(
            *[
                Text(str(i), font=MONO, font_size=16, color=TEAL).move_to(
                    register.get_left() + RIGHT * register.width * (i + 0.5) / 32
                )
                for i in range(32)
            ]
        )
        cell_count = Text(
            "256 bits / 8 bits per cell = 32 cells",
            font=SANS,
            font_size=32,
            color=TEAL,
        ).move_to(cell_size)
        final_caption = Text(
            "Each numbered lane holds one cell state.",
            font=SANS,
            font_size=23,
            color=MUTED,
        ).move_to(byte_caption)
        self.play(
            register.animate.set_fill(PALE_TEAL).set_stroke(TEAL),
            LaggedStart(*[Create(line) for line in byte_dividers], lag_ratio=0.025),
            run_time=1.3,
        )
        self.play(
            LaggedStart(*[FadeIn(label) for label in cell_labels], lag_ratio=0.015),
            ReplacementTransform(cell_size, cell_count),
            ReplacementTransform(byte_caption, final_caption),
            run_time=0.9,
        )
        self.wait(2)
