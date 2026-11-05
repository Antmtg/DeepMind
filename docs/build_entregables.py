"""Genera los entregables binarios de BioMonitor O2T.

Uso:
    python docs/build_entregables.py

Produce:
    docs/informe-final.pdf
    docs/presentacion-final.pptx

El PDF se construye desde docs/informe-final.md con un subconjunto de Markdown
(titulos, parrafos, listas, tablas, bloques de codigo, citas e imagenes). El PPTX
se construye con python-pptx y usa las capturas de docs/capturas cuando existen.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CAPTURES = DOCS / "capturas"
REPORT_MD = DOCS / "informe-final.md"
REPORT_PDF = DOCS / "informe-final.pdf"
PRESENTATION_PPTX = DOCS / "presentacion-final.pptx"

INK = "#0c161d"
TEAL = "#0f766e"
TEAL_SOFT = "#e6f4f1"
MUTED = "#5b6b73"
AMBER = "#b45309"
RED = "#b42318"


# ---------------------------------------------------------------------------
# Utilidades de Markdown
# ---------------------------------------------------------------------------


def inline_md(text: str) -> str:
    """Convierte un fragmento Markdown a marcado limitado de ReportLab."""
    parts = re.split(r"(`[^`]*`)", text)
    result: list[str] = []
    for part in parts:
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            code = escape(part[1:-1])
            result.append(
                f'<font name="Consolas" size="8.4" color="#334155">{code}</font>'
            )
            continue

        segment = escape(part)
        segment = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<link href="\2" color="#0f766e">\1</link>',
            segment,
        )
        segment = re.sub(
            r"&lt;(https?://[^&\s]+)&gt;",
            r'<link href="\1" color="#0f766e">\1</link>',
            segment,
        )
        segment = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", segment)
        result.append(segment)
    return "".join(result)


def plain_md(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("*", "")
    return text.strip()


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def build_pdf() -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        CondPageBreak,
        HRFlowable,
        Image,
        KeepTogether,
        PageBreak,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    fonts_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("SegoeUI", fonts_dir / "segoeui.ttf"))
    pdfmetrics.registerFont(TTFont("SegoeUI-Bold", fonts_dir / "segoeuib.ttf"))
    pdfmetrics.registerFont(TTFont("SegoeUI-Italic", fonts_dir / "segoeuii.ttf"))
    pdfmetrics.registerFont(TTFont("Consolas", fonts_dir / "consola.ttf"))
    pdfmetrics.registerFontFamily(
        "SegoeUI",
        normal="SegoeUI",
        bold="SegoeUI-Bold",
        italic="SegoeUI-Italic",
        boldItalic="SegoeUI-Bold",
    )

    body = ParagraphStyle(
        "Body",
        fontName="SegoeUI",
        fontSize=10.2,
        leading=15,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#1f2a30"),
        spaceAfter=7,
    )
    body_left = ParagraphStyle("BodyLeft", parent=body, alignment=TA_LEFT)
    h1 = ParagraphStyle(
        "H1",
        fontName="SegoeUI-Bold",
        fontSize=17,
        leading=22,
        textColor=colors.HexColor(TEAL),
        spaceBefore=6,
        spaceAfter=10,
    )
    h2 = ParagraphStyle(
        "H2",
        fontName="SegoeUI-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor(INK),
        spaceBefore=10,
        spaceAfter=6,
    )
    h3 = ParagraphStyle(
        "H3",
        fontName="SegoeUI-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#25313a"),
        spaceBefore=8,
        spaceAfter=4,
    )
    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        leftIndent=16,
        bulletIndent=4,
        spaceAfter=4,
        alignment=TA_LEFT,
    )
    quote = ParagraphStyle(
        "Quote",
        parent=body,
        fontName="SegoeUI-Italic",
        textColor=colors.HexColor(MUTED),
        leftIndent=14,
        borderPadding=6,
        borderColor=colors.HexColor("#cfe3de"),
        borderWidth=0,
        backColor=colors.HexColor("#f2f8f6"),
        spaceBefore=4,
        spaceAfter=8,
    )
    caption = ParagraphStyle(
        "Caption",
        fontName="SegoeUI-Italic",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor(MUTED),
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=12,
    )
    cover_meta = ParagraphStyle(
        "CoverMeta",
        fontName="SegoeUI",
        fontSize=11,
        leading=18,
        textColor=colors.HexColor("#d7e3e0"),
    )

    # Metadatos de la portada
    source = REPORT_MD.read_text(encoding="utf-8")
    lines = source.splitlines()
    first_h2 = next(
        (index for index, line in enumerate(lines) if line.startswith("## ")), 0
    )
    meta: list[tuple[str, str]] = []
    for line in lines[:first_h2]:
        match = re.match(r"\*\*(.+?):\*\*\s*(.*)", line.strip())
        if match:
            meta.append((match.group(1), match.group(2).strip()))
    md_body = lines[first_h2:]

    def cover(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(colors.HexColor(INK))
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor(TEAL))
        canvas.circle(width - 2.2 * cm, height - 2.5 * cm, 3.4 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#134e4a"))
        canvas.circle(1.2 * cm, 3.2 * cm, 4.2 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#99f6e4"))
        canvas.setFont("SegoeUI-Bold", 10)
        canvas.drawString(2 * cm, height - 4.2 * cm, "PROGRAMACIÓN 5 · SEMESTRE 5")
        canvas.setFillColor(colors.white)
        canvas.setFont("SegoeUI-Bold", 30)
        canvas.drawString(2 * cm, height - 7.3 * cm, "BioMonitor O₂T")
        canvas.setFillColor(colors.HexColor("#99f6e4"))
        canvas.setFont("SegoeUI", 14)
        canvas.drawString(
            2 * cm,
            height - 8.6 * cm,
            "Monitoreo de signos vitales con ESP32, separación por usuario y auditoría",
        )
        canvas.setStrokeColor(colors.HexColor(TEAL))
        canvas.setLineWidth(2)
        canvas.line(2 * cm, height - 9.4 * cm, width - 2 * cm, height - 9.4 * cm)
        y = height - 12.4 * cm
        for label, value in meta:
            canvas.setFillColor(colors.HexColor("#9fb3b0"))
            canvas.setFont("SegoeUI-Bold", 9.5)
            canvas.drawString(2 * cm, y, label.upper())
            canvas.setFillColor(colors.white)
            canvas.setFont("SegoeUI", 11)
            canvas.drawString(6.4 * cm, y, plain_md(value))
            y -= 0.85 * cm
        canvas.setFillColor(colors.HexColor("#9fb3b0"))
        canvas.setFont("SegoeUI", 9)
        canvas.drawString(2 * cm, 2 * cm, "Informe final · Documento académico")
        canvas.restoreState()

    def later_pages(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d8e3df"))
        canvas.setLineWidth(0.6)
        canvas.line(2 * cm, height - 1.55 * cm, width - 2 * cm, height - 1.55 * cm)
        canvas.setFont("SegoeUI", 8)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(2 * cm, height - 1.25 * cm, "BioMonitor O₂T · Informe final")
        canvas.drawRightString(
            width - 2 * cm, height - 1.25 * cm, "Programación 5 · Semestre 5"
        )
        canvas.line(2 * cm, 1.55 * cm, width - 2 * cm, 1.55 * cm)
        canvas.drawString(2 * cm, 1.15 * cm, "Herramienta académica de apoyo. No diagnostica.")
        canvas.drawRightString(width - 2 * cm, 1.15 * cm, f"Página {doc.page - 1}")
        canvas.restoreState()

    story: list = [PageBreak()]
    index = 0

    def add_table(rows: list[list[str]]) -> None:
        if not rows:
            return
        col_count = max(len(row) for row in rows)
        padded = [row + [""] * (col_count - len(row)) for row in rows]
        font_size = 7.1 if col_count >= 6 else 8.0 if col_count >= 4 else 8.8
        cell_style = ParagraphStyle(
            "Cell",
            fontName="SegoeUI",
            fontSize=font_size,
            leading=font_size + 2.2,
            textColor=colors.HexColor("#1f2a30"),
            splitLongWords=1,
        )
        header_style = ParagraphStyle(
            "CellHeader",
            parent=cell_style,
            fontName="SegoeUI-Bold",
            textColor=colors.white,
        )
        data = []
        for row_index, row in enumerate(padded):
            style = header_style if row_index == 0 else cell_style
            data.append([Paragraph(inline_md(cell), style) for cell in row])

        lengths = []
        for column in range(col_count):
            longest = max(len(plain_md(row[column])) for row in padded)
            lengths.append(max(6, min(longest, 55)))
        total = sum(lengths)
        available = A4[0] - 4 * cm
        widths = [available * length / total for length in lengths]
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(TEAL)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9d9d4")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f9f7")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        story.append(Spacer(1, 4))
        story.append(table)
        story.append(Spacer(1, 8))

    def add_image(path: Path, alt: str) -> None:
        try:
            width_px, height_px = ImageReader(str(path)).getSize()
        except Exception:
            return
        max_width = A4[0] - 4 * cm
        max_height = 19 * cm
        scale = min(max_width / width_px, max_height / height_px)
        image = Image(str(path), width=width_px * scale, height=height_px * scale)
        story.append(KeepTogether([image, Paragraph(escape(alt), caption)]))

    while index < len(md_body):
        raw = md_body[index].rstrip()
        stripped = raw.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            code_lines: list[str] = []
            while index < len(md_body) and not md_body[index].strip().startswith("```"):
                code_lines.append(md_body[index].rstrip("\n"))
                index += 1
            index += 1
            wrapped: list[str] = []
            for line in code_lines:
                wrapped.extend(textwrap.wrap(line, width=100) or [""])
            code_style = ParagraphStyle(
                "Code",
                fontName="Consolas",
                fontSize=8.1,
                leading=10.5,
                textColor=colors.HexColor("#173b3a"),
            )
            block = Table(
                [[Preformatted("\n".join(wrapped), code_style)]],
                colWidths=[A4[0] - 4 * cm],
            )
            block.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f7f5")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d3e4df")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.append(Spacer(1, 3))
            story.append(block)
            story.append(Spacer(1, 8))
            continue

        if stripped.startswith("|"):
            rows: list[list[str]] = []
            while index < len(md_body) and md_body[index].strip().startswith("|"):
                line = md_body[index].strip()
                if not re.match(r"^\|?[\s:|-]+\|?$", line):
                    rows.append(split_table_row(line))
                index += 1
            add_table(rows)
            continue

        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            image_path = (REPORT_MD.parent / image_match.group(2)).resolve()
            if image_path.exists():
                add_image(image_path, image_match.group(1))
            index += 1
            continue

        if stripped.startswith("### "):
            story.append(CondPageBreak(3.2 * cm))
            story.append(Paragraph(inline_md(stripped[4:]), h3))
            index += 1
            continue

        if stripped.startswith("## "):
            story.append(CondPageBreak(5 * cm))
            story.append(Paragraph(inline_md(stripped[3:]), h1))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.7,
                    color=colors.HexColor("#d8e3df"),
                    spaceBefore=1,
                    spaceAfter=8,
                )
            )
            index += 1
            continue

        if stripped.startswith("# "):
            story.append(Paragraph(inline_md(stripped[2:]), h1))
            index += 1
            continue

        if stripped.startswith(">"):
            quote_lines = []
            while index < len(md_body) and md_body[index].strip().startswith(">"):
                quote_lines.append(md_body[index].strip().lstrip(">").strip())
                index += 1
            story.append(Paragraph(inline_md(" ".join(quote_lines)), quote))
            continue

        if re.match(r"^[-*]\s+", stripped):
            while index < len(md_body):
                item = md_body[index].strip()
                if not re.match(r"^[-*]\s+", item):
                    break
                content = re.sub(r"^[-*]\s+", "", item)
                story.append(Paragraph(inline_md(content), bullet, bulletText="•"))
                index += 1
            story.append(Spacer(1, 3))
            continue

        numbered = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if numbered:
            while index < len(md_body):
                item = re.match(r"^(\d+)\.\s+(.*)", md_body[index].strip())
                if not item:
                    break
                story.append(
                    Paragraph(
                        inline_md(item.group(2)),
                        bullet,
                        bulletText=f"{item.group(1)}.",
                    )
                )
                index += 1
            story.append(Spacer(1, 3))
            continue

        if stripped == "---":
            story.append(Spacer(1, 4))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#e1ebe8"),
                    spaceBefore=2,
                    spaceAfter=6,
                )
            )
            index += 1
            continue

        # Párrafo: acumula líneas hasta una línea vacía o un bloque especial.
        paragraph_lines = [stripped]
        index += 1
        while index < len(md_body):
            candidate = md_body[index].strip()
            if (
                not candidate
                or candidate.startswith(("#", "|", "```", ">", "![", "- ", "* "))
                or re.match(r"^\d+\.\s+", candidate)
                or candidate == "---"
            ):
                break
            paragraph_lines.append(candidate)
            index += 1
        text = " ".join(paragraph_lines)
        text = re.sub(r"\s{2,}$", "", text)
        story.append(Paragraph(inline_md(text), body))

    # Anexo de capturas: se agregan las imágenes disponibles al final.
    capture_order = [
        "07-paciente-resumen",
        "01-paciente-graficas",
        "02-paciente-dos",
        "02b-paciente-dos-graficas",
        "03-cuidador-detalle",
        "03b-cuidador-graficas",
        "04-admin-sensores",
        "05-auditoria",
        "06-bienvenida",
    ]
    images = []
    for stem in capture_order:
        for extension in (".png", ".jpg"):
            candidate = CAPTURES / f"{stem}{extension}"
            if candidate.exists():
                images.append(candidate)
                break

    if images:
        story.append(CondPageBreak(6 * cm))
        story.append(Paragraph("Anexo B — Capturas de la aplicación", h1))
        story.append(
            Paragraph(
                "Capturas tomadas durante la verificación final en navegador. "
                "Los datos mostrados son de demostración o del simulador y se "
                "identifican como tales en la interfaz.",
                body,
            )
        )
        titles = {
            "07-paciente-resumen": "Panel del paciente: valores actuales, estado y última recepción.",
            "01-paciente-graficas": "Historial y gráficas del paciente con 10 lecturas del simulador.",
            "02-paciente-dos": "Segunda sesión de paciente: valores distintos y su propio sensor.",
            "02b-paciente-dos-graficas": "Gráficas de la segunda sesión, separadas de la primera.",
            "03-cuidador-detalle": "Detalle de paciente en el panel de cuidador.",
            "03b-cuidador-graficas": "Historial y gráficas dentro del detalle del cuidador.",
            "04-admin-sensores": "Panel de administración con el estado de contacto de los sensores.",
            "05-auditoria": "Auditoría filtrada por eventos de dispositivo.",
            "06-bienvenida": "Página pública de bienvenida.",
        }
        for image_path in images:
            caption_text = titles.get(image_path.stem, image_path.stem.replace("-", " ").title())
            add_image(image_path, caption_text)

    document = SimpleDocTemplate(
        str(REPORT_PDF),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.1 * cm,
        bottomMargin=2.1 * cm,
        title="BioMonitor O₂T — Informe final",
        author="Programación 5",
        subject="Monitoreo de signos vitales con ESP32",
    )
    document.build(
        story,
        onFirstPage=cover,
        onLaterPages=later_pages,
    )
    print(f"PDF generado: {REPORT_PDF}")


# ---------------------------------------------------------------------------
# PPTX
# ---------------------------------------------------------------------------


def build_pptx() -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.util import Inches, Pt

    def rgb(hex_value: str) -> RGBColor:
        hex_value = hex_value.lstrip("#")
        return RGBColor(int(hex_value[0:2], 16), int(hex_value[2:4], 16), int(hex_value[4:6], 16))

    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    blank = presentation.slide_layouts[6]

    def add_slide(background: str = "#ffffff"):
        slide = presentation.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = rgb(background)
        return slide

    def textbox(
        slide,
        left,
        top,
        width,
        height,
        text,
        size=18,
        bold=False,
        color=INK,
        align=PP_ALIGN.LEFT,
        font="Segoe UI",
        anchor=MSO_ANCHOR.TOP,
        line_spacing=1.05,
    ):
        box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        frame = box.text_frame
        frame.word_wrap = True
        frame.vertical_anchor = anchor
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        lines = text.split("\n")
        for index, line in enumerate(lines):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.alignment = align
            paragraph.line_spacing = line_spacing
            run = paragraph.add_run()
            run.text = line
            run.font.name = font
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = rgb(color)
        return box

    def bullets(slide, left, top, width, height, items, size=17, color=INK, gap=8):
        box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        for index, item in enumerate(items):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.space_after = Pt(gap)
            paragraph.line_spacing = 1.05
            run = paragraph.add_run()
            run.text = f"•  {item}"
            run.font.name = "Segoe UI"
            run.font.size = Pt(size)
            run.font.color.rgb = rgb(color)
        return box

    def kicker(slide, text, color=TEAL):
        textbox(slide, 0.75, 0.5, 8, 0.35, text.upper(), size=11, bold=True, color=color)

    def title(slide, text, top=0.85, size=31, color=INK):
        textbox(slide, 0.75, top, 11.8, 1.0, text, size=size, bold=True, color=color)

    def accent(slide, left=0.75, top=1.85, width=1.4, color=TEAL):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(0.06)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(color)
        shape.line.fill.background()

    def footer(slide, number):
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.75), Inches(7.02), Inches(11.83), Inches(0.012)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = rgb("#d8e3df")
        line.line.fill.background()
        textbox(slide, 0.75, 7.1, 6, 0.25, "BioMonitor O₂T · Programación 5", size=9, color=MUTED)
        textbox(slide, 11.6, 7.1, 1, 0.25, str(number), size=9, color=MUTED, align=PP_ALIGN.RIGHT)

    def add_table(slide, left, top, width, rows, col_widths=None, font_size=13):
        shape = slide.shapes.add_table(
            len(rows), len(rows[0]), Inches(left), Inches(top), Inches(width), Inches(0.4 * len(rows))
        )
        table = shape.table
        table.first_row = True
        table.horz_banding = False
        if col_widths:
            total = sum(col_widths)
            for index, col_width in enumerate(col_widths):
                table.columns[index].width = Inches(width * col_width / total)
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                cell = table.cell(row_index, col_index)
                cell.margin_left = Inches(0.08)
                cell.margin_right = Inches(0.08)
                cell.margin_top = Inches(0.03)
                cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(TEAL if row_index == 0 else ("#f4f9f7" if row_index % 2 == 0 else "#ffffff"))
                frame = cell.text_frame
                frame.word_wrap = True
                paragraph = frame.paragraphs[0]
                run = paragraph.add_run()
                run.text = value
                run.font.name = "Segoe UI"
                run.font.size = Pt(font_size)
                run.font.bold = row_index == 0
                run.font.color.rgb = rgb("#ffffff" if row_index == 0 else INK)
        return table

    def add_capture(slide, name, left, top, width, caption_text=None):
        candidates = [CAPTURES / f"{name}.png", CAPTURES / f"{name}.jpg"]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is None:
            box = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(3.1)
            )
            box.fill.solid()
            box.fill.fore_color.rgb = rgb("#f2f8f6")
            box.line.color.rgb = rgb("#cfe3de")
            textbox(
                slide,
                left + 0.3,
                top + 1.2,
                width - 0.6,
                0.7,
                "Captura pendiente",
                size=14,
                bold=True,
                color=MUTED,
                align=PP_ALIGN.CENTER,
            )
            return
        picture = slide.shapes.add_picture(str(path), Inches(left), Inches(top), width=Inches(width))
        if caption_text:
            textbox(
                slide,
                left,
                top + picture.height / 914400 + 0.05,
                width,
                0.3,
                caption_text,
                size=9,
                color=MUTED,
                align=PP_ALIGN.CENTER,
            )

    # 1. Portada
    slide = add_slide(INK)
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(10.8), Inches(-1.1), Inches(4.2), Inches(4.2))
    circle.fill.solid()
    circle.fill.fore_color.rgb = rgb(TEAL)
    circle.line.fill.background()
    circle2 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(-1.4), Inches(5.4), Inches(3.4), Inches(3.4))
    circle2.fill.solid()
    circle2.fill.fore_color.rgb = rgb("#134e4a")
    circle2.line.fill.background()
    textbox(slide, 0.8, 1.0, 10, 0.35, "PROGRAMACIÓN 5 · SEMESTRE 5", size=12, bold=True, color="#99f6e4")
    textbox(slide, 0.8, 1.5, 11, 1.2, "BioMonitor O₂T", size=52, bold=True, color="#ffffff")
    textbox(
        slide,
        0.8,
        2.9,
        9.8,
        1.0,
        "Monitoreo de signos vitales con ESP32, separación por usuario y auditoría",
        size=20,
        color="#d7e3e0",
    )
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(4.15), Inches(2.2), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb("#99f6e4")
    bar.line.fill.background()
    textbox(
        slide,
        0.8,
        4.55,
        8.5,
        1.4,
        "Integrantes: [Completar]\nDocente: [Completar]\nFecha: 4 de noviembre de 2026",
        size=14,
        color="#d7e3e0",
        line_spacing=1.3,
    )
    textbox(slide, 0.8, 6.75, 8, 0.3, "Informe y presentación final", size=10, color="#9fb3b0")
    slide.notes_slide.notes_text_frame.text = (
        "Abrir el panel ya iniciado en la sesión del paciente para que la demo esté lista."
    )

    # 2. Problema y objetivo
    slide = add_slide()
    kicker(slide, "Problema y objetivo")
    title(slide, "Un dato de salud sin contexto no es suficiente")
    accent(slide)
    textbox(
        slide,
        0.75,
        2.05,
        11.6,
        0.9,
        "Una lectura sin fecha, origen ni control de acceso puede llevar a decisiones equivocadas.",
        size=18,
        color=MUTED,
    )
    questions = [
        ("01", "¿El dato es actual?"),
        ("02", "¿De qué sensor viene?"),
        ("03", "¿Sigue conectado?"),
        ("04", "¿Quién puede verlo?"),
    ]
    for index, (number, question) in enumerate(questions):
        left = 0.75 + index * 3.02
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(3.25), Inches(2.75), Inches(1.55)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = rgb(TEAL_SOFT)
        card.line.fill.background()
        textbox(slide, left + 0.22, 3.45, 0.6, 0.4, number, size=12, bold=True, color=TEAL)
        textbox(slide, left + 0.22, 3.85, 2.3, 0.7, question, size=16, bold=True)
    textbox(
        slide,
        0.75,
        5.35,
        11.6,
        0.9,
        "Objetivo: recibir datos de dos ESP32, separarlos por usuario, mostrar su estado y conservar evidencia de auditoría.",
        size=17,
        bold=True,
        color=INK,
    )
    footer(slide, 2)
    slide.notes_slide.notes_text_frame.text = "Plantear las cuatro preguntas que guían el diseño del panel."

    # 3. Arquitectura
    slide = add_slide()
    kicker(slide, "Arquitectura")
    title(slide, "El servidor decide; el cliente solo presenta")
    accent(slide)

    def block(left, top, width, height, heading, detail, fill, text_color=INK):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill)
        shape.line.color.rgb = rgb("#cfe3de")
        textbox(slide, left + 0.2, top + 0.22, width - 0.4, 0.4, heading, size=15, bold=True, color=text_color)
        textbox(slide, left + 0.2, top + 0.72, width - 0.4, height - 0.9, detail, size=11.5, color=MUTED)

    block(0.75, 2.4, 3.25, 1.9, "ESP32 / simulador", "Lecturas con X-Device-Api-Key\nsource: esp32 · sensor_die · simulator", TEAL_SOFT)
    block(4.85, 2.4, 3.55, 1.9, "FastAPI", "JWT + RBAC\nDispositivos, mediciones,\nvínculos y auditoría", "#ffffff")
    block(9.25, 2.4, 3.0, 1.9, "SQLite", "users · devices\nmeasurements\ncare_assignments · audit_logs", "#f8faf9")
    for left in (3.95, 8.35):
        arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(left), Inches(3.15), Inches(0.75), Inches(0.4))
        arrow.fill.solid()
        arrow.fill.fore_color.rgb = rgb(TEAL)
        arrow.line.fill.background()
    block(0.75, 4.75, 5.6, 1.55, "Frontend HTML/CSS/JS", "Panel por rol, gráficas SVG, historial,\nestados de conexión y refresco cada 10 s.", "#ffffff")
    block(6.75, 4.75, 5.5, 1.55, "Auditoría", "LOGIN · ACCESS_DENIED · DEVICE_*\nSin contraseñas, tokens ni payloads.", TEAL_SOFT)
    footer(slide, 3)
    slide.notes_slide.notes_text_frame.text = "Enfatizar que el propietario se lee de devices.user_id, no del cuerpo del mensaje."

    # 4. Seguridad
    slide = add_slide()
    kicker(slide, "Seguridad implementada")
    title(slide, "Secretos protegidos y permisos en el servidor")
    accent(slide)
    left_items = [
        "Contraseñas con Argon2id.",
        "Sesión con JWT en cookie HttpOnly.",
        "RBAC en todas las rutas sensibles.",
        "Credenciales de dispositivo con HMAC-SHA256.",
    ]
    right_items = [
        "Código de emparejamiento temporal y de un solo uso.",
        "Propietario desde la base de datos, nunca del payload.",
        "Ingesta sin vincular: 409 + auditoría.",
        "Historial filtrado por el propietario actual.",
    ]
    bullets(slide, 0.9, 2.25, 5.6, 3.6, left_items, size=17, gap=13)
    bullets(slide, 6.9, 2.25, 5.6, 3.6, right_items, size=17, gap=13)
    note = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.75), Inches(5.7), Inches(11.6), Inches(0.75))
    note.fill.solid()
    note.fill.fore_color.rgb = rgb(TEAL_SOFT)
    note.line.fill.background()
    textbox(
        slide,
        1.0,
        5.87,
        11.1,
        0.4,
        "Auditoría de accesos, rechazos, emparejamientos y rotaciones, sin registrar secretos.",
        size=14,
        bold=True,
        color=TEAL,
    )
    footer(slide, 4)

    # 5. Dos usuarios, dos dispositivos
    slide = add_slide()
    kicker(slide, "Demostración simultánea")
    title(slide, "Dos usuarios, dos ESP32, datos separados")
    accent(slide)
    add_table(
        slide,
        0.75,
        2.15,
        7.1,
        [
            ["Dispositivo", "Propietario demo", "Perfil"],
            ["ESP32-O2T-01", "Paciente Demo", "SpO₂ 96–98 %"],
            ["ESP32-O2T-02", "Paciente Demo Dos", "SpO₂ 93–95 %"],
        ],
        col_widths=[1.4, 1.7, 1.3],
        font_size=13,
    )
    bullets(
        slide,
        8.25,
        2.15,
        4.2,
        3.8,
        [
            "Cada sensor tiene su propia api_key.",
            "Cada usuario ve solo su sensor y su historial.",
            "El simulador envía a ambos a la vez.",
            "La ingesta sin vincular se rechaza con 409.",
        ],
        size=14.5,
        gap=10,
    )
    for index, (label, value) in enumerate(
        [("SESIÓN A", "Paciente Demo · ESP32-O2T-01"), ("SESIÓN B", "Paciente Demo Dos · ESP32-O2T-02")]
    ):
        left = 0.9 + index * 6.0
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(4.45), Inches(5.35), Inches(1.1)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = rgb(TEAL_SOFT)
        card.line.fill.background()
        textbox(slide, left + 0.25, 4.62, 4.8, 0.25, label, size=10, bold=True, color=TEAL)
        textbox(slide, left + 0.25, 4.9, 4.8, 0.4, value, size=13.5, color=INK)
    footer(slide, 5)
    slide.notes_slide.notes_text_frame.text = "Mostrar las dos ventanas y el historial separado."

    # 6. Origen y estados
    slide = add_slide()
    kicker(slide, "Trazabilidad")
    title(slide, "Cada lectura conserva su origen")
    accent(slide)
    textbox(slide, 0.8, 2.15, 5.5, 0.4, "ORÍGENES VISIBLES", size=11, bold=True, color=TEAL)
    bullets(
        slide,
        0.8,
        2.55,
        5.4,
        3.7,
        [
            "ESP32 (sensor real)",
            "ESP32 · temperatura interna (no corporal)",
            "Simulador (datos simulados)",
            "Datos de ejemplo",
        ],
        size=16,
        gap=13,
    )
    textbox(slide, 7.0, 2.15, 5.3, 0.4, "ESTADOS DE CONEXIÓN", size=11, bold=True, color=TEAL)
    bullets(
        slide,
        7.0,
        2.55,
        5.3,
        3.7,
        [
            "Recibiendo datos (≤ 15 s)",
            "En línea, sin lectura nueva (≤ 90 s)",
            "Desconectado (> 90 s)",
            "Desactivado",
            "Sin lecturas",
        ],
        size=16,
        gap=11,
    )
    note = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.75), Inches(5.85), Inches(11.6), Inches(0.65))
    note.fill.solid()
    note.fill.fore_color.rgb = rgb("#fff7ed")
    note.line.fill.background()
    textbox(
        slide,
        1.0,
        6.0,
        11.1,
        0.35,
        "El panel nunca confunde una simulación con una medición física.",
        size=14,
        bold=True,
        color=AMBER,
    )
    footer(slide, 6)

    # 7. Historial y gráficas
    slide = add_slide()
    kicker(slide, "Historial y gráficas")
    title(slide, "Tendencias con tiempo, unidad y referencia")
    accent(slide)
    bullets(
        slide,
        0.8,
        2.15,
        5.0,
        4.3,
        [
            "Selector de 10, 30, 60 o 100 lecturas.",
            "Tres gráficas SVG: SpO₂, pulso y temperatura.",
            "Eje temporal, unidad y banda de referencia.",
            "Resumen de mínimo, máximo y último valor.",
            "Descripción accesible para lectores de pantalla.",
            "La temperatura interna se excluye de la gráfica corporal.",
        ],
        size=14.5,
        gap=10,
    )
    add_capture(slide, "02d-paciente-dos-graficas", 6.2, 2.15, 6.3, "Panel del paciente · 10 lecturas")
    footer(slide, 7)
    slide.notes_slide.notes_text_frame.text = "Cambiar el rango de historial y mostrar la actualización."

    # 8. Frecuencias y latencia
    slide = add_slide()
    kicker(slide, "Adquisición y refresco")
    title(slide, "Frecuencias documentadas y configurables")
    accent(slide)
    add_table(
        slide,
        0.75,
        2.15,
        7.2,
        [
            ["Etapa", "Valor"],
            ["Muestreo PPG", "100 Hz durante 4 s"],
            ["Envío al servidor", "Cada 5 s"],
            ["Heartbeat", "Cada 60 s"],
            ["Refresco del panel", "Cada 10 s"],
            ["Dato en vivo", "Última lectura ≤ 15 s"],
            ["Enlace activo", "Último contacto ≤ 90 s"],
        ],
        col_widths=[1.9, 1.0],
        font_size=13,
    )
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.45), Inches(2.15), Inches(4.0), Inches(2.0))
    card.fill.solid()
    card.fill.fore_color.rgb = rgb(TEAL_SOFT)
    card.line.fill.background()
    textbox(slide, 8.7, 2.35, 3.5, 0.3, "LATENCIA OBSERVADA", size=10, bold=True, color=TEAL)
    textbox(slide, 8.7, 2.75, 3.5, 0.7, "0–10 s", size=36, bold=True, color=TEAL)
    textbox(slide, 8.7, 3.45, 3.5, 0.5, "entre la ingesta y el panel, más red", size=11.5, color=MUTED)
    textbox(
        slide,
        8.45,
        4.55,
        4.0,
        1.7,
        "El botón «Actualizar» reduce la espera a la latencia de red. El firmware no envía lecturas inválidas.",
        size=12.5,
        color=MUTED,
    )
    footer(slide, 8)

    # 9. Resultados
    slide = add_slide()
    kicker(slide, "Resultados")
    title(slide, "62 pruebas y verificación en navegador")
    accent(slide)
    number_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.75), Inches(2.2), Inches(2.5), Inches(2.1))
    number_card.fill.solid()
    number_card.fill.fore_color.rgb = rgb(INK)
    number_card.line.fill.background()
    textbox(slide, 0.95, 2.45, 2.1, 0.9, "62", size=50, bold=True, color="#99f6e4")
    textbox(slide, 0.95, 3.45, 2.1, 0.5, "pruebas aprobadas", size=11, color="#d7e3e0")
    bullets(
        slide,
        3.7,
        2.15,
        5.4,
        4.3,
        [
            "Login/logout, RBAC y aislamiento verificados.",
            "Dos dispositivos simultáneos con datos separados.",
            "Historial y gráficas en paciente, cuidador y especialista.",
            "Administrador con estados de contacto.",
            "Auditoría con accesos, rechazos y eventos DEVICE_*.",
            "Firmware MAX30102/DS18B20 implementado.",
        ],
        size=13.5,
        gap=8,
    )
    add_capture(slide, "04-admin-sensores", 9.15, 2.1, 3.45, "Estado de sensores")
    footer(slide, 9)

    # 10. Correcciones
    slide = add_slide()
    kicker(slide, "Correcciones del cierre")
    title(slide, "Qué cambió y por qué")
    accent(slide)
    corrections = [
        ("01", "Claves en texto plano", "HMAC-SHA256 con SECRET_KEY."),
        ("02", "Demo marcada como esp32", "Ahora source=\"demo\"."),
        ("03", "Ingesta sin dueño", "Rechazo 409 + auditoría."),
        ("04", "Historial del dueño anterior", "Filtro por propietario actual."),
        ("05", "Firmware aleatorio por defecto", "Lectura real o nada."),
        ("06", "Sin gráficas ni historial", "SVG con referencia y resumen."),
        ("07", "Refresco apagado", "Activo cada 10 s."),
    ]
    for index, (number, before, after) in enumerate(corrections):
        column = index % 2
        row = index // 2
        left = 0.75 + column * 6.05
        top = 2.1 + row * 1.08
        textbox(slide, left, top, 0.45, 0.35, number, size=12, bold=True, color=TEAL)
        textbox(slide, left + 0.5, top - 0.03, 2.7, 0.5, before, size=11.5, bold=True)
        textbox(slide, left + 3.35, top - 0.03, 2.55, 0.7, after, size=11, color=MUTED)
    footer(slide, 10)

    # 11. Limitaciones
    slide = add_slide()
    kicker(slide, "Limitaciones y trabajo futuro")
    title(slide, "Lo implementado y lo que falta validar")
    accent(slide)
    textbox(slide, 0.8, 2.15, 5.4, 0.4, "LIMITACIONES", size=11, bold=True, color=RED)
    bullets(
        slide,
        0.8,
        2.55,
        5.4,
        3.6,
        [
            "MAX30102 y DS18B20 sin validación física.",
            "Fórmula SpO₂ de banco, no certificada.",
            "SQLite para un prototipo académico.",
            "Sin notificaciones ni app móvil nativa.",
        ],
        size=15,
        gap=11,
    )
    textbox(slide, 7.0, 2.15, 5.3, 0.4, "TRABAJO FUTURO", size=11, bold=True, color=TEAL)
    bullets(
        slide,
        7.0,
        2.55,
        5.3,
        3.6,
        [
            "Calibrar contra un oximétro de referencia.",
            "Grabar el video de respaldo.",
            "Migrar a PostgreSQL si crece la concurrencia.",
            "Crear cuentas desde la interfaz.",
        ],
        size=15,
        gap=11,
    )
    footer(slide, 11)

    # 12. Conclusiones
    slide = add_slide(INK)
    textbox(slide, 0.8, 0.8, 11, 0.35, "CONCLUSIONES", size=12, bold=True, color="#99f6e4")
    textbox(slide, 0.8, 1.35, 11.5, 1.8, "Un dato con origen, fecha y control de acceso", size=36, bold=True, color="#ffffff")
    bullets(
        slide,
        0.9,
        3.15,
        11.2,
        2.6,
        [
            "El servidor es la autoridad de permisos y asociación.",
            "Cada lectura conserva su origen y su fecha.",
            "Dos usuarios y dos dispositivos conviven sin mezclar datos.",
            "El panel responde: ¿qué?, ¿cuándo?, ¿de dónde?, ¿sigue conectado?",
        ],
        size=16,
        color="#d7e3e0",
        gap=10,
    )
    textbox(slide, 0.8, 6.15, 11.5, 0.6, "“No mostramos un dato sin decir de dónde viene ni cuándo llegó.”", size=15, bold=True, color="#99f6e4")
    textbox(slide, 0.8, 6.9, 3, 0.3, "Preguntas", size=10, color="#9fb3b0")

    # 13. Guion de demo
    slide = add_slide()
    kicker(slide, "Demostración")
    title(slide, "Guion de cinco minutos")
    accent(slide)
    steps = [
        ("1", "Sesión A: paciente 1 con ESP32-O2T-01."),
        ("2", "Sesión B: paciente 2 con ESP32-O2T-02."),
        ("3", "Mostrar origen simulador en la tabla."),
        ("4", "Cambiar el historial a 60 lecturas."),
        ("5", "Detener el simulador y esperar 90 s."),
        ("6", "Reiniciar y ver «Recibiendo datos»."),
        ("7", "Abrir cuidador, administrador y auditoría."),
        ("8", "Cerrar con la idea central del proyecto."),
    ]
    for index, (number, text) in enumerate(steps):
        column = index % 2
        row = index // 2
        left = 0.85 + column * 6.0
        top = 2.15 + row * 1.05
        circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(left), Inches(top), Inches(0.5), Inches(0.5))
        circle.fill.solid()
        circle.fill.fore_color.rgb = rgb(TEAL)
        circle.line.fill.background()
        textbox(slide, left, top + 0.1, 0.5, 0.3, number, size=12, bold=True, color="#ffffff", align=PP_ALIGN.CENTER)
        textbox(slide, left + 0.7, top + 0.08, 4.9, 0.6, text, size=13.5)
    footer(slide, 13)

    presentation.save(str(PRESENTATION_PPTX))
    print(f"PPTX generado: {PRESENTATION_PPTX}")


if __name__ == "__main__":
    build_pdf()
    build_pptx()
