from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "ui_detailed_design.md"
TARGET = ROOT / "docs" / "ui_detailed_design.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 44
MARGIN_TOP = 52
MARGIN_BOTTOM = 48
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN_X * 2)

FONT_BODY = "HYGothic-Medium"
FONT_TITLE = "HYSMyeongJo-Medium"


def register_fonts() -> None:
    pdfmetrics.registerFont(UnicodeCIDFont(FONT_BODY))
    pdfmetrics.registerFont(UnicodeCIDFont(FONT_TITLE))


def text_width(text: str, font: str, size: int) -> float:
    return pdfmetrics.stringWidth(text, font, size)


def wrap_text(text: str, font: str, size: int, max_width: float) -> list[str]:
    text = text.rstrip()
    if not text:
        return [""]

    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and text_width(candidate, font, size) > max_width:
            lines.append(current.rstrip())
            current = char.lstrip()
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return lines


class PdfWriter:
    def __init__(self, output: Path) -> None:
        self.canvas = canvas.Canvas(str(output), pagesize=A4)
        self.page_number = 0
        self.y = 0.0
        self.new_page()

    def new_page(self) -> None:
        if self.page_number:
            self.canvas.showPage()
        self.page_number += 1
        self.y = PAGE_HEIGHT - MARGIN_TOP
        self.canvas.setStrokeColor(colors.HexColor("#d6ded9"))
        self.canvas.line(MARGIN_X, PAGE_HEIGHT - 34, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 34)
        self.canvas.setFont(FONT_BODY, 8)
        self.canvas.setFillColor(colors.HexColor("#6c7a76"))
        self.canvas.drawRightString(PAGE_WIDTH - MARGIN_X, 22, f"SoriCall UI Detailed Design · {self.page_number}")
        self.canvas.setFillColor(colors.black)

    def ensure_space(self, height: float) -> None:
        if self.y - height < MARGIN_BOTTOM:
            self.new_page()

    def draw_wrapped(
        self,
        text: str,
        font: str = FONT_BODY,
        size: int = 10,
        leading: int = 15,
        color: str = "#203336",
        indent: int = 0,
        before: int = 0,
        after: int = 0,
        max_width: float | None = None,
    ) -> None:
        width = max_width if max_width is not None else CONTENT_WIDTH - indent
        lines = wrap_text(text, font, size, width)
        self.ensure_space(before + after + (len(lines) * leading))
        self.y -= before
        self.canvas.setFont(font, size)
        self.canvas.setFillColor(colors.HexColor(color))
        for line in lines:
            self.canvas.drawString(MARGIN_X + indent, self.y, line)
            self.y -= leading
        self.y -= after
        self.canvas.setFillColor(colors.black)

    def draw_rule(self) -> None:
        self.ensure_space(18)
        self.canvas.setStrokeColor(colors.HexColor("#d6ded9"))
        self.canvas.line(MARGIN_X, self.y, PAGE_WIDTH - MARGIN_X, self.y)
        self.y -= 18

    def save(self) -> None:
        self.canvas.save()


def clean_inline(text: str) -> str:
    return (
        text.replace("`", "")
        .replace("**", "")
        .replace("<br>", " ")
        .replace("&nbsp;", " ")
    )


def render_markdown(source: Path, target: Path) -> None:
    writer = PdfWriter(target)
    in_code = False

    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()

        if line.startswith("```"):
            in_code = not in_code
            if in_code:
                writer.ensure_space(18)
                writer.y -= 6
            else:
                writer.y -= 8
            continue

        if in_code:
            writer.draw_wrapped(line, size=8, leading=12, color="#30464a", indent=12, max_width=CONTENT_WIDTH - 24)
            continue

        if not line:
            writer.y -= 6
            if writer.y < MARGIN_BOTTOM:
                writer.new_page()
            continue

        if line.startswith("# "):
            writer.draw_wrapped(clean_inline(line[2:]), font=FONT_TITLE, size=22, leading=28, color="#123438", before=4, after=10)
            writer.draw_rule()
            continue

        if line.startswith("## "):
            writer.draw_wrapped(clean_inline(line[3:]), font=FONT_TITLE, size=16, leading=22, color="#126b68", before=12, after=4)
            continue

        if line.startswith("### "):
            writer.draw_wrapped(clean_inline(line[4:]), font=FONT_BODY, size=12, leading=17, color="#173437", before=8, after=2)
            continue

        if line.startswith("|"):
            if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
                continue
            writer.draw_wrapped(clean_inline(line), size=8, leading=12, color="#263c40", indent=4)
            continue

        if line.startswith("- "):
            writer.draw_wrapped("- " + clean_inline(line[2:]), size=10, leading=15, color="#263c40", indent=8)
            continue

        if line[0:2].isdigit() and ". " in line[:5]:
            writer.draw_wrapped(clean_inline(line), size=10, leading=15, color="#263c40", indent=8)
            continue

        writer.draw_wrapped(clean_inline(line), size=10, leading=15, color="#263c40")

    writer.save()


def main() -> None:
    register_fonts()
    render_markdown(SOURCE, TARGET)
    print(TARGET)


if __name__ == "__main__":
    main()
