#!/usr/bin/env python3
"""Generate a CDUT-template-based thesis main draft from the canonical Markdown.

The source template is never modified. The cover and declaration pages retain
the approved front-matter text from the current formal DOCX, while the generated
portion begins with the Chinese abstract and excludes acknowledgements and
publications by design. Appendices retain supporting data.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import copy
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_LINE_SPACING,
    WD_TAB_ALIGNMENT,
    WD_TAB_LEADER,
)
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/thesis/thesis-manuscript.md"
DEFAULT_TEMPLATE = Path("/Users/xushuyuan/Downloads/1.成都理工大学专业学位硕士学位论文模板20230905(1).docx")
DEFAULT_OUTPUT = ROOT / "outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式论文.docx"
DEFAULT_COVER_SOURCE = DEFAULT_OUTPUT
MAX_HAN_CHARACTERS = 51_000

EAST_ASIA = "宋体"
ENGLISH = "Times New Roman"
HEADING_FONT = "黑体"
TITLE = "基于站内多关系图与机制诊断的充电节点短期负荷预测研究"
ENGLISH_TITLE = "Short-Term Load Forecasting of Charging Nodes Based on Within-Station Multi-Relation Graphs and Mechanism Diagnosis"
NODE = "/Users/xushuyuan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
MATH_CONVERTER = ROOT / "scripts/latex_to_omml.js"
MATH_NODE_PATH = os.environ.get(
    'THESIS_MATH_NODE_PATH',
    os.pathsep.join((str(Path(NODE).parent.parent / 'node_modules'),
                     str(Path.home() / '.local/share/evcs-document-runtimes/math/node_modules'),
                     '/private/tmp/codex-thesis-math-runtime/node_modules')),
)


def validate_math_runtime():
    """Fail before assembling the document if the formula runtime is incomplete."""
    env = os.environ.copy()
    env['NODE_PATH'] = MATH_NODE_PATH
    check = (
        'const missing=["docx","temml","fast-xml-parser"].filter(n=>'
        '{try{require.resolve(n);return false;}catch{return true;}});'
        'if(missing.length){console.error("Missing math modules: "+missing.join(", "));process.exit(1);}'
    )
    result = subprocess.run([NODE, '-e', check], env=env, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError('Formula runtime preflight failed: ' + result.stderr.strip()[:500])


def validate_final_figure_sequence(source_text: str) -> None:
    """Reject missing, duplicated, or out-of-order manuscript figure numbers."""
    captions = [(int(ch), int(num)) for ch, num in re.findall(r"\*\*图(\d+)-(\d+)\b", source_text)]
    image_paths = re.findall(r"!\[[^]]*\]\(([^)]+)\)", source_text)
    chapter_counts = ((1, 2), (2, 13), (3, 17), (4, 7), (5, 9))
    figure_count = sum(count for _, count in chapter_counts)
    if len(captions) != figure_count or len(image_paths) != figure_count:
        raise RuntimeError(
            f"Expected {figure_count} figures and captions, found {len(image_paths)} images and {len(captions)} captions"
        )
    expected = []
    for chapter, count in chapter_counts:
        expected.extend((chapter, number) for number in range(1, count + 1))
    if captions != expected:
        raise RuntimeError("Figure captions are not in strict chapter order from 图1-1 to 图5-9")
    for (chapter, number), path in zip(captions, image_paths):
        if f"fig{chapter}_{number}_" not in Path(path).name:
            raise RuntimeError(f"Figure path does not match 图{chapter}-{number}: {path}")


def set_font(run, name=EAST_ASIA, size=12, bold=None, italic=None):
    run.font.name = ENGLISH
    rfonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    rfonts.set(qn("w:ascii"), ENGLISH)
    rfonts.set(qn("w:hAnsi"), ENGLISH)
    rfonts.set(qn("w:cs"), ENGLISH)
    rfonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_paragraph_format(p, align=None, first_line=True, before=0, after=0, line=1.25):
    pf = p.paragraph_format
    if align is not None:
        p.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    # The template's 16.3 pt grid can double the requested 15 pt line height
    # in office renderers. Respect the explicit paragraph spacing instead.
    ppr = p._p.get_or_add_pPr()
    snap = ppr.find(qn("w:snapToGrid"))
    if snap is None:
        snap = OxmlElement("w:snapToGrid")
        ppr.append(snap)
    snap.set(qn("w:val"), "0")
    if first_line:
        pf.first_line_indent = Pt(24)
    else:
        pf.first_line_indent = Cm(0)


def paragraph(doc, text="", *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line=True, size=12, bold=False, font=EAST_ASIA, style=None, superscript_citations=True):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    set_paragraph_format(p, align, first_line)
    parts = re.split(r"(\[(?:\d+(?:\s*[-,，]\s*\d+)*)\])", text) if superscript_citations else [text]
    for part in parts:
        if not part:
            continue
        r = p.add_run(part)
        set_font(r, font, size, bold)
        if superscript_citations and re.fullmatch(r"\[(?:\d+(?:\s*[-,，]\s*\d+)*)\]", part):
            r.font.superscript = True
    return p


def add_page_field(paragraph_):
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), ENGLISH)
    fonts.set(qn("w:hAnsi"), ENGLISH)
    fonts.set(qn("w:eastAsia"), EAST_ASIA)
    rpr.append(fonts)
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "18")
    rpr.append(size)
    run.append(rpr)
    text = OxmlElement("w:t")
    text.text = "1"  # Cached value; the PAGE field is recalculated on rendering.
    run.append(text)
    fld.append(run)
    paragraph_._p.append(fld)


def set_page_number_format(section, fmt, start=None):
    """Set an explicit page-number restart for a Word section."""
    sect_pr = section._sectPr
    existing = sect_pr.find(qn("w:pgNumType"))
    if existing is not None:
        sect_pr.remove(existing)
    element = OxmlElement("w:pgNumType")
    element.set(qn("w:fmt"), fmt)
    if start is not None:
        element.set(qn("w:start"), str(start))
    sect_pr.append(element)


def add_header_rule(paragraph_):
    ppr = paragraph_._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in {"val": "single", "sz": "4", "space": "1", "color": "000000"}.items():
        bottom.set(qn("w:" + key), value)
    borders.append(bottom)
    ppr.append(borders)


def configure_header(paragraph_, text):
    paragraph_.clear()
    paragraph_.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_format(paragraph_, WD_ALIGN_PARAGRAPH.CENTER, False, before=0, after=0, line=1.0)
    r = paragraph_.add_run(text)
    set_font(r, EAST_ASIA, 9)
    add_header_rule(paragraph_)


def configure_section(section, *, odd_header, even_header="成都理工大学硕士学位论文", page_format="decimal", start=None, page_number=True):
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.75)
    section.header.is_linked_to_previous = False
    section.even_page_header.is_linked_to_previous = False
    configure_header(section.header.paragraphs[0], odd_header)
    configure_header(section.even_page_header.paragraphs[0], even_header)
    for footer in (section.footer, section.even_page_footer):
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0]
        fp.clear()
        set_paragraph_format(fp, WD_ALIGN_PARAGRAPH.CENTER, False, line=1.0)
        fp.add_run().font.size = Pt(9)
        if page_number:
            add_page_field(fp)
    set_page_number_format(section, page_format, start)


def add_toc_field(paragraph_):
    """Embed an updateable Word TOC field without a visible placeholder message."""
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    paragraph_._p.append(begin)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    paragraph_._p.append(instr)
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    paragraph_._p.append(separate)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    paragraph_._p.append(end)


TOC_TAB_POSITION = Cm(14.66)  # A4 text width under the template's 3.17 cm margins.
TOC_LEVEL_LAYOUT = {
    # CDUT contents: level 1 flush left, level 2/3 indented by two/four
    # Chinese characters.  Do not use hanging indents: wrapped rows follow
    # the same left edge as the entry text.
    1: Cm(0.00),
    2: Cm(0.85),
    3: Cm(1.69),
}
TOC_LEVEL_SIZE = {1: 12, 2: 12, 3: 12}


def _append_field_char(paragraph_, field_type):
    run = OxmlElement("w:r")
    fld_char = OxmlElement("w:fldChar")
    fld_char.set(qn("w:fldCharType"), field_type)
    run.append(fld_char)
    paragraph_._p.append(run)


def _append_field_instruction(paragraph_):
    run = OxmlElement("w:r")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    run.append(instr)
    paragraph_._p.append(run)


def _configure_toc_paragraph(paragraph_, level):
    """Apply stable paragraph geometry shared by cached and visible TOC rows."""
    set_paragraph_format(
        paragraph_, WD_ALIGN_PARAGRAPH.LEFT, False, before=0, after=0, line=1.25
    )
    paragraph_.paragraph_format.left_indent = TOC_LEVEL_LAYOUT[level]
    paragraph_.paragraph_format.first_line_indent = Cm(0)
    paragraph_.paragraph_format.tab_stops.add_tab_stop(
        TOC_TAB_POSITION, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
    )


def configure_toc_styles(doc):
    """Keep a WPS/Word field refresh from reverting the required TOC format."""
    for level in (1, 2, 3):
        style = doc.styles[f"toc {level}"]
        style.font.name = ENGLISH
        style.font.size = Pt(12)
        style.font.bold = level == 1
        rfonts = style.element.get_or_add_rPr().get_or_add_rFonts()
        rfonts.set(qn("w:ascii"), ENGLISH)
        rfonts.set(qn("w:hAnsi"), ENGLISH)
        rfonts.set(qn("w:cs"), ENGLISH)
        rfonts.set(qn("w:eastAsia"), EAST_ASIA)
        pf = style.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.25
        ppr = style.element.get_or_add_pPr()
        snap = ppr.find(qn("w:snapToGrid"))
        if snap is None:
            snap = OxmlElement("w:snapToGrid")
            ppr.append(snap)
        snap.set(qn("w:val"), "0")
        pf.left_indent = TOC_LEVEL_LAYOUT[level]
        pf.first_line_indent = Cm(0)
        pf.tab_stops.add_tab_stop(
            TOC_TAB_POSITION, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
        )


def _add_toc_entry(paragraph_, level, text, page):
    size = TOC_LEVEL_SIZE[level]
    run = paragraph_.add_run(text)
    set_font(run, EAST_ASIA, size, bold=(level == 1))
    if page:
        tab = paragraph_.add_run()
        tab.add_tab()
        page_run = paragraph_.add_run(page)
        set_font(page_run, EAST_ASIA, size, bold=(level == 1))


def add_cached_toc_field(doc, source, page_map=None):
    """Embed a native TOC field whose cached result uses one paragraph per row.

    Word/WPS can update the field, while headless LibreOffice can render the
    cached page-mapped result.  The field result is deliberately split into
    real paragraphs so TOC styles, hanging indents, and right-aligned leader
    tabs remain structural rather than simulated with spaces or dot characters.
    """
    entries = toc_entries(source, page_map)
    for index, (level, text, page) in enumerate(entries):
        paragraph_ = doc.add_paragraph(style=f"toc {level}")
        _configure_toc_paragraph(paragraph_, level)
        if index == 0:
            _append_field_char(paragraph_, "begin")
            _append_field_instruction(paragraph_)
            _append_field_char(paragraph_, "separate")
        _add_toc_entry(paragraph_, level, text, page)
        if index == len(entries) - 1:
            _append_field_char(paragraph_, "end")


def set_cell_border(cell, **kwargs):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge, spec in kwargs.items():
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        for key, value in spec.items():
            element.set(qn("w:" + key), str(value))


NONE = {"val": "nil"}
THIN = {"val": "single", "sz": "6", "color": "000000"}
THICK = {"val": "single", "sz": "12", "color": "000000"}
TABLE_WIDTH_CM = 14.66
TABLE_FONT_SIZE = 10.5


def _set_table_width(table, width_cm=TABLE_WIDTH_CM):
    """Set both table/grid/cell geometry to the template's text width."""
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    width_twips = int(round(width_cm * 567))
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.insert(0, tbl_w)
    tbl_w.set(qn("w:w"), str(width_twips))
    tbl_w.set(qn("w:type"), "dxa")
    col_width = width_cm / len(table.columns)
    for column in table.columns:
        column.width = Cm(col_width)
    for row in table.rows:
        for cell in row.cells:
            cell.width = Cm(col_width)


def _set_table_row_rules(row, *, repeat_header=False):
    """Repeat the header on continuation pages and keep each row intact."""
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = tr_pr.find(qn("w:cantSplit"))
    if cant_split is None:
        tr_pr.append(OxmlElement("w:cantSplit"))
    if repeat_header and tr_pr.find(qn("w:tblHeader")) is None:
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        tr_pr.append(header)


def add_three_line_table(doc, rows):
    if len(rows) < 2:
        return
    cols = max(len(x) for x in rows)
    table = doc.add_table(rows=0, cols=cols)
    _set_table_width(table)
    widths = [Cm(TABLE_WIDTH_CM / cols) for _ in range(cols)]
    for ri, values in enumerate(rows):
        cells = table.add_row().cells
        _set_table_row_rules(table.rows[-1], repeat_header=(ri == 0))
        for ci in range(cols):
            cell = cells[ci]
            cell.width = widths[ci]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            set_paragraph_format(p, WD_ALIGN_PARAGRAPH.CENTER, False, line=1.0)
            # Long evidence tables may continue on another page. Keep the
            # header with its first data row; avoid chaining every row into an
            # oversized block. Each individual row remains intact.
            p.paragraph_format.keep_with_next = (ri == 0 or (len(rows) <= 7 and ri < len(rows) - 1))
            cell_text = clean_inline(values[ci] if ci < len(values) else "")
            if cols >= 5 and ri > 0:
                # Break at a semantic boundary, never in a decimal's digits.
                if re.fullmatch(r"\d+\.\d+±\d+\.\d+", cell_text):
                    cell_text = cell_text.replace("±", "\n±")
                elif re.fullmatch(r"mrg_[a-z_]+", cell_text) and len(cell_text) >= 12:
                    cell_text = cell_text.replace("mrg_", "mrg_\n", 1)
            # Numeric in-text references inside tables follow the same
            # superscript convention as body citations. Split them into their
            # own runs so the formatting survives DOCX generation.
            parts = re.split(r"(\[(?:\d+(?:\s*[-,，]\s*\d+)*)\])", cell_text)
            for part in parts:
                if not part:
                    continue
                r = p.add_run(part)
                set_font(r, EAST_ASIA, TABLE_FONT_SIZE, bold=(ri == 0))
                if re.fullmatch(r"\[(?:\d+(?:\s*[-,，]\s*\d+)*)\]", part):
                    r.font.superscript = True
            set_cell_border(cell, top=THICK if ri == 0 else NONE,
                            bottom=THIN if ri == 0 else (THICK if ri == len(rows) - 1 else NONE),
                            left=NONE, right=NONE)
    _set_table_width(table)
    return table


MATH_REPL = {
    r"\\alpha": "α", r"\\beta": "β", r"\\gamma": "γ", r"\\delta": "δ", r"\\Delta": "Δ",
    r"\\theta": "θ", r"\\Theta": "Θ", r"\\lambda": "λ", r"\\mu": "μ", r"\\sigma": "σ",
    r"\\Sigma": "Σ", r"\\phi": "φ", r"\\Phi": "Φ", r"\\varepsilon": "ε", r"\\times": "×",
    r"\\pm": "±", r"\\le": "≤", r"\\ge": "≥", r"\\approx": "≈", r"\\in": "∈",
    r"\\rightarrow": "→", r"\\leftarrow": "←", r"\\sum": "∑", r"\\Vert": "‖", r"\\odot": "⊙",
    r"\\sigma": "σ", r"\\max": "max ",
    r"\\min": "min ", r"\\operatorname": "", r"\\mathrm": "", r"\\mathbf": "", r"\\boldsymbol": "", r"\\mathbb": "",
    r"\\mathcal": "", r"\\mathsf": "", r"\\text": "", r"\\widehat": "", r"\\hat": "",
    r"\\ldots": "…", r"\\cdot": "·", r"\\,": " ", r"\\!": "", r"\\;": " ",
}


def clean_math(text):
    tag = re.search(r"\\tag\{([^}]+)\}", text)
    number = tag.group(1) if tag else ""
    text = re.sub(r"\\tag\{[^}]+\}", "", text)
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", text)
    text = re.sub(r"\\(?:left|right)", "", text)
    for source, target in MATH_REPL.items():
        # Keys are raw LaTeX spellings; source manuscripts contain one backslash.
        text = text.replace(source.replace("\\\\", "\\"), target)
    # Remove LaTeX wrappers only after named commands have been translated.
    text = re.sub(r"\\(?:operatorname|mathrm|mathbf|boldsymbol|mathcal|mathsf|text|widehat|hat)\{([^{}]*)\}", r"\1", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, number


def add_omml_text(paragraph_, formula):
    """Insert native Word OMML.  Unicode math text remains editable in Word."""
    math = OxmlElement("m:oMath")
    run = OxmlElement("m:r")
    run_pr = OxmlElement("m:rPr")
    font = OxmlElement("w:rFonts")
    font.set(qn("w:ascii"), "Cambria Math")
    font.set(qn("w:hAnsi"), "Cambria Math")
    run_pr.append(font)
    run.append(run_pr)
    text = OxmlElement("m:t")
    text.text = formula
    run.append(text)
    math.append(run)
    paragraph_._p.append(math)


def latex_to_omml(latex):
    """Use Temml plus the DOCX skill's MathML converter to retain formula structure."""
    env = {**__import__("os").environ, "NODE_PATH": MATH_NODE_PATH}
    result = subprocess.run(
        [NODE, str(MATH_CONVERTER)], input=latex.encode("utf-8"), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env, check=True,
    )
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(result.stdout))) as package:
        xml = package.read("word/document.xml")
    root = __import__("lxml.etree", fromlist=["etree"]).fromstring(xml)
    ns = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
    math = root.xpath(".//m:oMath", namespaces=ns)[0]
    return parse_xml(__import__("lxml.etree", fromlist=["etree"]).tostring(math))


def sanitize_review_artifacts(input_docx: Path, output_docx: Path):
    """Remove legacy template comments and the red cover authoring prompt."""
    from lxml import etree

    w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    comment_tags = {
        f"{{{w_ns}}}commentRangeStart",
        f"{{{w_ns}}}commentRangeEnd",
        f"{{{w_ns}}}commentReference",
    }
    excluded = {
        "word/comments.xml",
        "word/commentsExtended.xml",
        "word/commentsIds.xml",
        "word/people.xml",
    }

    with zipfile.ZipFile(input_docx) as source, zipfile.ZipFile(
        output_docx, "w", compression=zipfile.ZIP_DEFLATED
    ) as target:
        for item in source.infolist():
            name = item.filename
            if name in excluded:
                continue
            data = source.read(name)
            if name.endswith(".xml") or name.endswith(".rels"):
                try:
                    root = etree.fromstring(data)
                except etree.XMLSyntaxError:
                    target.writestr(item, data)
                    continue

                for element in list(root.iter()):
                    if element.tag in comment_tags and element.getparent() is not None:
                        element.getparent().remove(element)

                if name.startswith("word/") and name.endswith(".xml"):
                    ns = {"w": w_ns}
                    for run in root.xpath('.//w:r[normalize-space(string(.))="（必填）"]', namespaces=ns):
                        parent = run.getparent()
                        if parent is not None:
                            parent.remove(run)
                    for track in root.xpath('.//w:trackRevisions', namespaces=ns):
                        parent = track.getparent()
                        if parent is not None:
                            parent.remove(track)

                if name.endswith(".rels"):
                    for rel in root.findall(f"{{{rel_ns}}}Relationship"):
                        value = (rel.get("Type", "") + rel.get("Target", "")).lower()
                        if "comment" in value or "people" in value:
                            root.remove(rel)

                if name == "[Content_Types].xml":
                    for override in root.findall(f"{{{ct_ns}}}Override"):
                        value = override.get("PartName", "").lower()
                        if "comment" in value or "people" in value:
                            root.remove(override)

                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            target.writestr(item, data)


def add_equation(doc, latex):
    formula, number = clean_math(latex)
    table = doc.add_table(rows=1, cols=3)
    table.autofit = False
    # Inner text width is 14.66 cm under the CDUT template's 3.17 cm side margins.
    widths = [Cm(0.6), Cm(13.46), Cm(0.6)]
    for cell, width in zip(table.rows[0].cells, widths):
        cell.width = width
        set_cell_border(cell, top=NONE, bottom=NONE, left=NONE, right=NONE)
    formula_cell = table.cell(0, 1)
    p = formula_cell.paragraphs[0]
    set_paragraph_format(p, WD_ALIGN_PARAGRAPH.CENTER, False, line=1.0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    p.paragraph_format.line_spacing = Pt(18)
    # This is a short-lived build placeholder.  The deterministic second pass
    # replaces the whole numbered table with one native OMML paragraph.
    r = p.add_run(formula)
    set_font(r, ENGLISH, 10.5)
    if number:
        p = table.cell(0, 2).paragraphs[0]
        set_paragraph_format(p, WD_ALIGN_PARAGRAPH.RIGHT, False, line=1.1)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
        p.paragraph_format.line_spacing = Pt(18)
        r = p.add_run("（" + number + "）")
        set_font(r, EAST_ASIA, 10.5)


def clean_inline(text):
    text = text.strip()
    text = text.replace("**", "")
    # Preserve an explicit delimiter for the native-OMML second pass.  Stripping
    # the delimiter here irreversibly flattens subscripts, superscripts and
    # mathematical alphabets into ordinary text.
    text = re.sub(r"\$([^$]+)\$", r"\\(\1\\)", text)
    text = text.replace("`", "")
    return text


def toc_entries(source, page_map=None):
    """Return the visible three-level TOC items from the canonical manuscript."""
    entries = []
    lines = source.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("# 第1章"))
    end = next(i for i, line in enumerate(lines) if line.startswith("# 在读期间"))
    for line in lines[start:end]:
        match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if not match:
            continue
        level, text = len(match.group(1)), clean_inline(match.group(2))
        if level == 1 and text in {"摘  要", "Abstract", "目  录", "致  谢", "在读期间发表的学术论文及研究成果", "附录"}:
            continue
        if level == 1 and not text.startswith(("第", "附录")) and text != "结  论" and text != "参考文献":
            continue
        entries.append((level, text, str((page_map or {}).get(text, ""))))
    return entries


def add_visible_toc(doc, source, page_map=None):
    """Create a readable structural TOC without a native field."""
    for level, text, page in toc_entries(source, page_map):
        p = doc.add_paragraph(style=f"toc {level}")
        _configure_toc_paragraph(p, level)
        _add_toc_entry(p, level, text, page)


def add_figure(doc, path, alt, source_dir):
    png = (source_dir / path).resolve()
    if png.suffix.lower() == ".svg":
        png = png.with_suffix(".png")
    if not png.exists():
        raise FileNotFoundError(png)
    # Approved conversation redraws must not silently regress to script outputs.
    registry = png.parent / 'priority-review-20260907/imagegen_provenance.json'
    if registry.exists():
        import hashlib
        import json
        image_hash = hashlib.sha256(png.read_bytes()).hexdigest()
        dpi_manifest_path = ROOT / 'docs/thesis/figure-1200dpi-20261007.json'
        dpi_delivery_hash = None
        if dpi_manifest_path.exists():
            dpi_manifest = json.loads(dpi_manifest_path.read_text())
            relative_path = png.relative_to(ROOT).as_posix()
            dpi_delivery_hash = next(
                (
                    item.get('delivery_sha256')
                    for item in dpi_manifest.get('figures', [])
                    if item.get('path') == relative_path
                ),
                None,
            )
        for entry in json.loads(registry.read_text())['entries']:
            # A later deterministic academic redraw is intentionally allowed
            # to supersede the earlier ImageGen preview. The 1200-DPI delivery
            # raster is also allowed when its exact hash is registered.
            if entry['stem'] == png.stem and entry.get('source_type', 'imagegen') == 'imagegen':
                if image_hash not in {entry['sha256'], dpi_delivery_hash}:
                    raise ValueError(f'Approved figure hash mismatch: {png}')
    p = doc.add_paragraph()
    set_paragraph_format(p, WD_ALIGN_PARAGRAPH.CENTER, False, before=3, after=3, line=1.0)
    r = p.add_run()
    p.paragraph_format.keep_with_next = True
    # Keep the figure just inside 14.2 cm. This avoids a one-pixel rounding
    # shortfall below 1200 effective PPI for 1200-DPI rasters such as fig5_3.
    # The change is visually negligible and remains within the 14.66 cm body width.
    r.add_picture(str(png), width=Cm(14.19))


def add_heading(doc, level, text, outline=True):
    # The supplied template does not define every built-in Heading style.  Set an
    # explicit outline level instead, so Word's TOC field remains reliable.
    # Front-matter labels may look like headings but must remain ordinary
    # paragraphs; applying Heading 1 makes WPS insert them into the native TOC.
    p = doc.add_paragraph(style="Heading 1" if level == 1 and outline else None)
    if outline:
        ppr = p._p.get_or_add_pPr()
        outline_level = OxmlElement("w:outlineLvl")
        outline_level.set(qn("w:val"), str(min(level - 1, 8)))
        ppr.append(outline_level)
    if level == 1:
        set_paragraph_format(p, WD_ALIGN_PARAGRAPH.CENTER, False, before=12, after=3, line=1.0)
    elif level == 2:
        set_paragraph_format(p, WD_ALIGN_PARAGRAPH.JUSTIFY, False, before=18, after=12, line=1.5)
    elif level == 3:
        set_paragraph_format(p, WD_ALIGN_PARAGRAPH.JUSTIFY, False, before=12, after=9, line=1.25)
    else:
        set_paragraph_format(p, WD_ALIGN_PARAGRAPH.JUSTIFY, False, before=12, after=6, line=1.25)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.keep_together = True
    r = p.add_run(text)
    heading_font = "楷体" if level == 4 else HEADING_FONT
    set_font(r, heading_font, {1: 18, 2: 15, 3: 14, 4: 12}[level], bold=(level != 3))
    return p


def parse_table(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", x.replace(" ", "")) for x in cells):
            rows.append(cells)
        i += 1
    return rows, i


def add_body(doc, source):
    lines = source.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("# 第1章"))
    end = next(i for i, line in enumerate(lines) if line.startswith("# 在读期间"))
    i = start
    skip_acknowledgements = False
    while i < end:
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.startswith("!["):
            match = re.match(r"!\[([^]]+)\]\(([^)]+)\)", line)
            if match:
                add_figure(doc, match.group(2), match.group(1), source.parent)
            i += 1
            continue
        if line.startswith("|"):
            rows, i = parse_table(lines, i)
            add_three_line_table(doc, rows)
            continue
        if line in ("\\[", "$$"):
            close = "\\]" if line == "\\[" else "$$"
            content = []
            i += 1
            while i < end and lines[i].strip() != close:
                content.append(lines[i])
                i += 1
            add_equation(doc, " ".join(content))
            i += 1
            continue
        h = re.match(r"^(#{1,4})\s+(.+)$", line)
        if h:
            level, text = len(h.group(1)), h.group(2)
            if level == 1 and text == "致  谢":
                skip_acknowledgements = True
                i += 1
                continue
            if level == 1 and text == "参考文献":
                skip_acknowledgements = False
            if skip_acknowledgements:
                i += 1
                continue
            is_terminal_section = re.sub(r"\s+", "", text) in {"结论", "参考文献"}
            if level == 1 and (text.startswith(("第", "附录")) or is_terminal_section):
                doc.add_section(WD_SECTION.NEW_PAGE)
                configure_section(doc.sections[-1], odd_header=clean_inline(text), start=1 if text.startswith("第1章") else None)
            add_heading(doc, level, clean_inline(text))
            i += 1
            continue
        if skip_acknowledgements:
            i += 1
            continue
        is_named_table_caption = line.startswith((
            "**数据协议回答范围表**",
            "**原主实验配置与证据来源表**",
            "**原主实验时间块误差差复核表**",
        ))
        if line.startswith("**图") or line.startswith("**表") or is_named_table_caption:
            text = clean_inline(line)
            split = re.split(r"\s{2,}", text, maxsplit=1)
            title = split[0]
            note = split[1] if len(split) > 1 else ""
            title = re.sub(r"(图\d+-\d+)b\b", r"\1（b）", title)
            is_subfigure = bool(re.match(r"^图\d+-\d+（[a-z]）", title))
            # Variants such as 图2-3（b） belong to the preceding main figure;
            # keep their visual caption but do not create a second numbered target.
            p = doc.add_paragraph()
            set_paragraph_format(p, WD_ALIGN_PARAGRAPH.CENTER, False, before=3, after=3, line=1.0)
            # Keep a table title with at least the first row; Word/WPS can then
            # move the table cleanly when a page ends immediately before it.
            if title.startswith("表") or is_named_table_caption or (title.startswith("图") and note):
                p.paragraph_format.keep_with_next = True
            r = p.add_run(title + ("：" if is_subfigure else ""))
            set_font(r, HEADING_FONT, 10.5, bold=False)
            if note:
                # “注：”既符合学校图表注口径，也避免审计器将 9 pt 图注
                # 误识别为 12 pt 正文。
                note_paragraph = paragraph(doc, "注：" + note, first_line=True, size=9)
                note_paragraph.paragraph_format.keep_together = True
            i += 1
            continue
        if re.match(r"^\[\d+\]", line):
            p = paragraph(doc, clean_inline(line), align=WD_ALIGN_PARAGRAPH.LEFT,
                          first_line=False, size=10.5, superscript_citations=False)
            p.paragraph_format.left_indent = Cm(0.74)
            p.paragraph_format.first_line_indent = Cm(-0.74)
            p.paragraph_format.line_spacing = 1.25
            i += 1
            continue
        if line.startswith(">"):
            i += 1
            continue
        paragraph(doc, clean_inline(line), size=12)
        i += 1


def remove_template_body_after_declarations(doc):
    # Paragraph 60 is the template's trailing empty section-break paragraph;
    # paragraph 61 is the first inner-page placeholder (论文题目).  Removing
    # from paragraph 60 avoids leaving two consecutive section breaks, which
    # otherwise renders as a blank page before the abstract.
    body = doc._element.body
    anchor = doc.paragraphs[60]._p
    children = list(body)
    for child in children[children.index(anchor):]:
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def copy_approved_cover_content(doc, source_path: Path):
    """Copy only the approved cover/declaration paragraph content from the
    current formal DOCX, preserving the CDUT template's paragraph properties.

    The author, advisor, degree field, and student number are already confirmed
    in the current formal document. Unknown cover fields remain blank, and the
    signature/date lines remain unsigned. Copying run XML preserves the
    template's underlining, fonts, and spacing without carrying over stale body
    content or tables.
    """
    if not source_path.is_file():
        raise FileNotFoundError(f"approved cover source not found: {source_path}")
    cover_source = Document(source_path)
    if len(doc.paragraphs) < 60 or len(cover_source.paragraphs) < 60:
        raise RuntimeError("Template and approved cover source must contain at least 60 front-matter paragraphs")
    source_text = "\n".join(p.text for p in cover_source.paragraphs[:60])
    required = (
        "基于站内多关系图与机制诊断的",
        "充电节点短期负荷预测研究",
        "胥舒元",
        "杨小峰（副教授）",
        "电气工程",
        "2024050524",
    )
    missing = [value for value in required if value not in source_text]
    if missing:
        raise RuntimeError(f"approved cover source is missing confirmed fields: {missing}")

    for index in range(60):
        target_p = doc.paragraphs[index]._p
        source_p = cover_source.paragraphs[index]._p
        # The approved formal DOCX carries a manual page break before the
        # copyright authorization page.  Preserve that one layout control;
        # without it WPS can pull the page onto the declaration page and leave
        # a spurious blank page before the abstract.
        source_ppr = source_p.pPr
        target_ppr = target_p.get_or_add_pPr()
        target_page_break = target_ppr.find(qn("w:pageBreakBefore"))
        if target_page_break is not None:
            target_ppr.remove(target_page_break)
        source_page_break = source_ppr.find(qn("w:pageBreakBefore")) if source_ppr is not None else None
        if source_page_break is not None:
            target_ppr.append(copy.deepcopy(source_page_break))

        # The university logotype is an embedded drawing in the template.
        # Keep the template's own relationship at paragraph 3: copying the
        # source drawing XML here can point its rId at a different image and
        # make the mark disappear in WPS/PDF.
        preserved_template_logo_runs = []
        if index == 3:
            preserved_template_logo_runs = [
                copy.deepcopy(child)
                for child in target_p
                if child.tag == qn("w:r") and child.xpath(".//w:drawing")
            ]
        for child in list(target_p):
            if child.tag != qn("w:pPr"):
                target_p.remove(child)
        for child in list(source_p):
            if child.tag != qn("w:pPr") and not (index == 3 and child.xpath(".//w:drawing")):
                target_p.append(copy.deepcopy(child))
        for logo_run in preserved_template_logo_runs:
            target_p.append(logo_run)


def remove_template_protection(doc):
    settings = doc.settings.element
    protection = settings.find(qn("w:documentProtection"))
    if protection is not None:
        settings.remove(protection)


def clear_front_matter_headers(doc):
    """Remove template placeholder headers from cover and declaration pages."""
    for section in doc.sections[:3]:
        section.header.is_linked_to_previous = False
        section.even_page_header.is_linked_to_previous = False
        for header in (section.header, section.even_page_header):
            for p in header.paragraphs:
                p.clear()


def compact_outer_cover_spacing(doc):
    """Keep the template date on the outer cover without changing its content."""
    for index in (2, 6, 7):
        p = doc.paragraphs[index]
        if not p.text and not p._p.xpath('.//w:drawing | .//w:sectPr'):
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = Pt(14)


def add_front_matter(doc, source, toc_map=None):
    doc.add_section(WD_SECTION.NEW_PAGE)
    configure_section(doc.sections[-1], odd_header="摘  要", page_format="upperRoman", start=1)
    zh_title = add_heading(doc, 1, TITLE, outline=False)
    set_paragraph_format(zh_title, WD_ALIGN_PARAGRAPH.CENTER, False, before=0, after=0, line=1.0)
    set_font(zh_title.runs[0], HEADING_FONT, 15, bold=True)
    zh_heading = add_heading(doc, 1, "摘  要", outline=False)
    set_paragraph_format(zh_heading, WD_ALIGN_PARAGRAPH.CENTER, False, before=18, after=18, line=1.0)
    set_font(zh_heading.runs[0], EAST_ASIA, 15, bold=True)
    source_text = source.read_text(encoding="utf-8")
    cn = source_text.split("# 摘  要", 1)[1].split("# Abstract", 1)[0]
    for x in [x.strip() for x in cn.split("\n\n") if x.strip()]:
        if x.startswith("关键词："):
            paragraph(doc, clean_inline(x), first_line=False, size=12, bold=True)
        else:
            paragraph(doc, clean_inline(x), size=12)
    doc.add_section(WD_SECTION.NEW_PAGE)
    # 英文摘要与中文摘要连续使用大写罗马页码，不在本节重新从 I 开始。
    configure_section(doc.sections[-1], odd_header="Abstract", page_format="upperRoman")
    en_title = add_heading(doc, 1, ENGLISH_TITLE, outline=False)
    set_paragraph_format(en_title, WD_ALIGN_PARAGRAPH.CENTER, False, before=0, after=0, line=1.0)
    set_font(en_title.runs[0], ENGLISH, 15, bold=True)
    en_heading = add_heading(doc, 1, "Abstract", outline=False)
    set_paragraph_format(en_heading, WD_ALIGN_PARAGRAPH.CENTER, False, before=18, after=18, line=1.0)
    set_font(en_heading.runs[0], ENGLISH, 15, bold=True)
    en = source_text.split("# Abstract", 1)[1].split("# 目  录", 1)[0]
    for x in [x.strip() for x in en.split("\n\n") if x.strip()]:
        if x.startswith("Keywords:"):
            paragraph(doc, clean_inline(x), first_line=False, size=12, bold=True, font=ENGLISH)
        else:
            paragraph(doc, clean_inline(x), size=12, font=ENGLISH)
    doc.add_section(WD_SECTION.NEW_PAGE)
    # The body heading supplies the single visible TOC title.  Reusing the same
    # text as the odd-page header produced a duplicated "目 录" on the first
    # contents page in WPS/LibreOffice exports.
    configure_section(
        doc.sections[-1],
        odd_header="成都理工大学硕士学位论文",
        page_format="lowerRoman",
        start=1,
    )
    # The contents title is visually a chapter-level heading, but it must not
    # inherit Heading 1 or appear as an entry in the navigation pane/TOC.
    toc_heading = doc.add_paragraph()
    set_paragraph_format(toc_heading, WD_ALIGN_PARAGRAPH.CENTER, False, before=24, after=18, line=1.0)
    toc_title_run = toc_heading.add_run("目  录")
    set_font(toc_title_run, HEADING_FONT, 18, bold=True)
    # Keep a native TOC field for Word/WPS updates, while embedding its current
    # page-mapped result so headless PDF export is also populated.  The cached
    # result is emitted as one actual paragraph per entry.
    add_cached_toc_field(doc, source, toc_map)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--cover-source",
        type=Path,
        default=DEFAULT_COVER_SOURCE,
        help="current formal DOCX containing the confirmed cover fields; only its first 60 paragraph contents are copied",
    )
    parser.add_argument("--toc-map", type=Path, help="JSON mapping of heading text to final Arabic page number")
    args = parser.parse_args()
    if not args.template.exists():
        raise FileNotFoundError(args.template)
    validate_math_runtime()
    source_text = args.source.read_text(encoding="utf-8")
    han_characters = len(re.findall(r"[\u4e00-\u9fff]", source_text))
    if han_characters > MAX_HAN_CHARACTERS:
        raise RuntimeError(
            f"Thesis exceeds the 51,000-character limit: {han_characters} Chinese characters"
        )
    print(f"Chinese character count: {han_characters}/{MAX_HAN_CHARACTERS}")
    validate_final_figure_sequence(source_text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    from rebuild_docx_formulas import extract_tagged_formulas, rebuild
    expected_display_formulas = len(extract_tagged_formulas(source_text))

    # Build and validate off-path, then replace the single canonical output only
    # after every tagged display equation and recognized inline expression has
    # been converted successfully.  No versioned intermediate DOCX is retained.
    with tempfile.TemporaryDirectory(prefix="thesis-docx-build-") as build_dir:
        base_docx = Path(build_dir) / "base.docx"
        fixed_docx = Path(build_dir) / "fixed.docx"
        sanitized_docx = Path(build_dir) / "sanitized.docx"
        shutil.copy2(args.template, base_docx)
        doc = Document(base_docx)
        doc.core_properties.title = TITLE
        doc.core_properties.author = ""
        doc.core_properties.last_modified_by = ""
        remove_template_protection(doc)
        settings = doc.settings.element
        if settings.find(qn("w:evenAndOddHeaders")) is None:
            settings.append(OxmlElement("w:evenAndOddHeaders"))
        if settings.find(qn("w:updateFields")) is None:
            update_fields = OxmlElement("w:updateFields")
            update_fields.set(qn("w:val"), "true")
            settings.append(update_fields)
        remove_template_body_after_declarations(doc)
        copy_approved_cover_content(doc, args.cover_source)
        clear_front_matter_headers(doc)
        compact_outer_cover_spacing(doc)
        configure_toc_styles(doc)
        toc_map = json.loads(args.toc_map.read_text(encoding="utf-8")) if args.toc_map else None
        add_front_matter(doc, args.source, toc_map)
        add_body(doc, args.source)
        doc.save(base_docx)
        formula_report = rebuild(
            base_docx, args.source, fixed_docx, NODE, MATH_CONVERTER, MATH_NODE_PATH
        )
        if (
            formula_report["conversion_errors"]
            or formula_report["display_formulas"] != expected_display_formulas
        ):
            raise RuntimeError(
                "Native formula rebuild failed: "
                f"expected {expected_display_formulas} tagged display equations; "
                f"report={formula_report}"
            )
        sanitize_review_artifacts(fixed_docx, sanitized_docx)
        shutil.move(sanitized_docx, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
