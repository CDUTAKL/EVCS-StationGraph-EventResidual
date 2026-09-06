#!/usr/bin/env python3
"""Generate a CDUT-template-based thesis main draft from the canonical Markdown.

The source template is never modified.  Cover pages and declarations are retained
as supplied; the generated portion begins with the Chinese abstract and excludes
acknowledgements, publications, and appendices by design.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import shutil
import subprocess
import copy
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/thesis/thesis-manuscript.md"
DEFAULT_TEMPLATE = Path("/Users/xushuyuan/Downloads/1.成都理工大学专业学位硕士学位论文模板20230905(1).docx")
DEFAULT_OUTPUT = ROOT / "outputs/thesis/基于站内多关系图与机制诊断的充电节点短期负荷预测研究_正式排版版_43图优化版.docx"

EAST_ASIA = "宋体"
ENGLISH = "Times New Roman"
HEADING_FONT = "黑体"
TITLE = "基于站内多关系图与机制诊断的充电节点短期负荷预测研究"
NODE = "/Users/xushuyuan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
MATH_CONVERTER = ROOT / "scripts/latex_to_omml.js"
MATH_NODE_PATH = "/private/tmp/codex-thesis-math-runtime/node_modules"


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
    section.footer.is_linked_to_previous = False
    configure_header(section.header.paragraphs[0], odd_header)
    configure_header(section.even_page_header.paragraphs[0], even_header)
    fp = section.footer.paragraphs[0]
    fp.clear()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
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


def add_three_line_table(doc, rows):
    if len(rows) < 2:
        return
    cols = max(len(x) for x in rows)
    table = doc.add_table(rows=0, cols=cols)
    table.autofit = False
    widths = [Cm(16.15 / cols) for _ in range(cols)]
    for ri, values in enumerate(rows):
        cells = table.add_row().cells
        for ci in range(cols):
            cell = cells[ci]
            cell.width = widths[ci]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            set_paragraph_format(p, WD_ALIGN_PARAGRAPH.CENTER if ri == 0 else WD_ALIGN_PARAGRAPH.LEFT, False, line=1.15)
            r = p.add_run(clean_inline(values[ci] if ci < len(values) else ""))
            set_font(r, EAST_ASIA, 9.5, bold=(ri == 0))
            set_cell_border(cell, top=THICK if ri == 0 else NONE,
                            bottom=THIN if ri == 0 else (THICK if ri == len(rows) - 1 else NONE),
                            left=NONE, right=NONE)
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
        if level == 1 and not text.startswith("第") and text != "结  论" and text != "参考文献":
            continue
        entries.append((level, text, str((page_map or {}).get(text, ""))))
    return entries


def add_visible_toc(doc, source, page_map=None):
    """Create a readable fallback TOC; Word may replace it by updating the field."""
    for level, text, page in toc_entries(source, page_map):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm({1: 0, 2: 0.65, 3: 1.3}[level])
        set_paragraph_format(p, WD_ALIGN_PARAGRAPH.LEFT, False, before=0, after=0, line=1.0)
        r = p.add_run(text)
        set_font(r, EAST_ASIA, 11 if level == 1 else 10.5, bold=(level == 1))
        if page:
            dots = "·" * max(3, 50 - len(text) * 2)
            r = p.add_run(dots + page)
            set_font(r, EAST_ASIA, 10.5)


def add_figure(doc, path, alt, source_dir):
    png = (source_dir / path).resolve()
    if png.suffix.lower() == ".svg":
        png = png.with_suffix(".png")
    if not png.exists():
        raise FileNotFoundError(png)
    p = doc.add_paragraph()
    set_paragraph_format(p, WD_ALIGN_PARAGRAPH.CENTER, False, before=3, after=3, line=1.0)
    r = p.add_run()
    # Inner-page width is 14.66 cm under the template's 3.17 cm side margins.
    r.add_picture(str(png), width=Cm(14.2))


def add_heading(doc, level, text, outline=True):
    # The supplied template does not define every built-in Heading style.  Set an
    # explicit outline level instead, so Word's TOC field remains reliable.
    p = doc.add_paragraph(style="Heading 1" if level == 1 else None)
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
    r = p.add_run(text)
    set_font(r, HEADING_FONT, {1: 18, 2: 15, 3: 14, 4: 12}[level], bold=(level != 3))
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
            if level == 1 and (text.startswith("第") or is_terminal_section):
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
            r = p.add_run(title + ("：" if is_subfigure else ""))
            set_font(r, HEADING_FONT, 10.5, bold=False)
            if note:
                # “注：”既符合学校图表注口径，也避免审计器将 9 pt 图注
                # 误识别为 12 pt 正文。
                paragraph(doc, "注：" + note, first_line=True, size=9)
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
            paragraph(doc, x, first_line=False, size=12, bold=True)
        else:
            paragraph(doc, x, size=12)
    doc.add_section(WD_SECTION.NEW_PAGE)
    # 英文摘要与中文摘要连续使用大写罗马页码，不在本节重新从 I 开始。
    configure_section(doc.sections[-1], odd_header="Abstract", page_format="upperRoman")
    en_title = add_heading(doc, 1, TITLE, outline=False)
    set_paragraph_format(en_title, WD_ALIGN_PARAGRAPH.CENTER, False, before=0, after=0, line=1.0)
    set_font(en_title.runs[0], ENGLISH, 15, bold=True)
    en_heading = add_heading(doc, 1, "Abstract", outline=False)
    set_paragraph_format(en_heading, WD_ALIGN_PARAGRAPH.CENTER, False, before=18, after=18, line=1.0)
    set_font(en_heading.runs[0], ENGLISH, 15, bold=True)
    en = source_text.split("# Abstract", 1)[1].split("# 目  录", 1)[0]
    for x in [x.strip() for x in en.split("\n\n") if x.strip()]:
        if x.startswith("Keywords:"):
            paragraph(doc, x, first_line=False, size=12, bold=True, font=ENGLISH)
        else:
            paragraph(doc, x, size=12, font=ENGLISH)
    doc.add_section(WD_SECTION.NEW_PAGE)
    configure_section(doc.sections[-1], odd_header="目  录", page_format="lowerRoman", start=1)
    toc_heading = add_heading(doc, 1, "目  录", outline=False)
    set_paragraph_format(toc_heading, WD_ALIGN_PARAGRAPH.CENTER, False, before=24, after=18, line=1.0)
    toc_field = doc.add_paragraph()
    set_paragraph_format(toc_field, WD_ALIGN_PARAGRAPH.LEFT, False, line=1.0)
    add_toc_field(toc_field)
    # Keep only the native Word TOC field in the formal manuscript.  A visible
    # fallback list would be mistaken for body headings by the CDUT auditor and
    # would duplicate the TOC after Word refreshes the field.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--toc-map", type=Path, help="JSON mapping of heading text to final Arabic page number")
    args = parser.parse_args()
    if not args.template.exists():
        raise FileNotFoundError(args.template)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    from rebuild_docx_formulas import rebuild

    # Build and validate off-path, then replace the single canonical output only
    # after all 23 display equations and every recognized inline expression have
    # been converted successfully.  No versioned intermediate DOCX is retained.
    with tempfile.TemporaryDirectory(prefix="thesis-docx-build-") as build_dir:
        base_docx = Path(build_dir) / "base.docx"
        fixed_docx = Path(build_dir) / "fixed.docx"
        sanitized_docx = Path(build_dir) / "sanitized.docx"
        shutil.copy2(args.template, base_docx)
        doc = Document(base_docx)
        remove_template_protection(doc)
        settings = doc.settings.element
        if settings.find(qn("w:evenAndOddHeaders")) is None:
            settings.append(OxmlElement("w:evenAndOddHeaders"))
        if settings.find(qn("w:updateFields")) is None:
            update_fields = OxmlElement("w:updateFields")
            update_fields.set(qn("w:val"), "true")
            settings.append(update_fields)
        remove_template_body_after_declarations(doc)
        clear_front_matter_headers(doc)
        toc_map = json.loads(args.toc_map.read_text(encoding="utf-8")) if args.toc_map else None
        add_front_matter(doc, args.source, toc_map)
        add_body(doc, args.source)
        doc.save(base_docx)
        formula_report = rebuild(
            base_docx, args.source, fixed_docx, NODE, MATH_CONVERTER, MATH_NODE_PATH
        )
        if formula_report["conversion_errors"] or formula_report["display_formulas"] != 23:
            raise RuntimeError(f"Native formula rebuild failed: {formula_report}")
        sanitize_review_artifacts(fixed_docx, sanitized_docx)
        shutil.move(sanitized_docx, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
