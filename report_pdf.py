"""Convert the Markdown analysis report to a PDF with embedded Unicode fonts."""

import argparse
import os
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import TextStyle
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent


def find_fonts() -> list[Path]:
    candidates = [
        (Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts",
         ["arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"]),
        (Path("/usr/share/fonts/truetype/dejavu"),
         ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
          "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf"]),
        (Path("/System/Library/Fonts/Supplemental"),
         ["Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf"]),
    ]
    for directory, names in candidates:
        paths = [directory / name for name in names]
        if all(path.is_file() for path in paths):
            return paths
    raise RuntimeError("PDF fonts not found. Install Arial or DejaVu Sans.")


def convert_report(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Report is empty: {source}")
    pdf = FPDF()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    for style, path in zip(("", "B", "I", "BI"), find_fonts()):
        pdf.add_font("Report", style=style, fname=str(path))
    pdf.set_font("Report", size=11)
    pdf.set_title("YouTube comment analysis")
    pdf.add_page()
    # Reports contain untrusted comment text. Render Markdown without raw HTML
    # or images so conversion never fetches external resources or local files.
    renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
    renderer.disable("image")
    pdf.write_html(
        renderer.render(text), font_family="Report",
        tag_styles={"code": TextStyle(font_family="Report"),
                    "pre": TextStyle(font_family="Report")},
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Convert one Markdown file instead of both reports.")
    parser.add_argument("--output", type=Path, help="Output path for a single report.")
    args = parser.parse_args()
    if args.input or args.output:
        source = args.input or ROOT / "data" / "analysis.md"
        reports = [(source, args.output or source.with_suffix(".pdf"))]
    else:
        reports = [
            (ROOT / "data" / "analysis.md", ROOT / "data" / "ru_analysis.pdf"),
            (ROOT / "data" / "en_analysis.md", ROOT / "data" / "en_analysis.pdf"),
        ]
    for source, output in reports:
        convert_report(source, output)
        print(f"PDF report: {output}")


if __name__ == "__main__":
    main()
