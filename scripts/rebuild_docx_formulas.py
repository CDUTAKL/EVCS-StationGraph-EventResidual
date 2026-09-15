#!/usr/bin/env python3
"""Rebuild inline and numbered equations in the thesis main DOCX as native OMML.

The main draft is treated as the content authority.  This script changes only
word/document.xml: all other DOCX parts, including images, headers, sections,
references, and existing layout metadata, are copied unchanged.
"""
from __future__ import annotations

import argparse
import base64
import io
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W_NS, "m": M_NS}
W = f"{{{W_NS}}}"
M = f"{{{M_NS}}}"


def extract_tagged_formulas(markdown: str) -> dict[str, str]:
    """Extract all tagged display equations from the canonical manuscript."""
    formulas: dict[str, str] = {}
    patterns = (r"\$\$(.*?)\$\$", r"\\\[(.*?)\\\]")
    for pattern in patterns:
        for match in re.finditer(pattern, markdown, flags=re.S):
            block = match.group(1).strip()
            tag = re.search(r"\\tag\{([^}]+)\}", block)
            if not tag:
                continue
            key = tag.group(1)
            formulas[key] = re.sub(r"\\tag\{[^}]+\}", "", block).strip()
    return formulas


def run_converter(latex: str, node: str, converter: str, node_path: str) -> etree._Element:
    env = dict(os.environ)
    env["NODE_PATH"] = node_path
    result = subprocess.run(
        [node, converter],
        input=latex.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    try:
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(result.stdout))) as package:
            xml = package.read("word/document.xml")
    except Exception as exc:  # pragma: no cover - defensive conversion guard
        raise RuntimeError(f"converter returned invalid DOCX payload: {exc}") from exc
    root = etree.fromstring(xml)
    math = root.xpath(".//m:oMath", namespaces=NS)
    if not math:
        raise RuntimeError("converter returned no m:oMath element")
    result = etree.fromstring(etree.tostring(math[0]))
    repair_empty_nary(result)
    return result


def repair_empty_nary(math: etree._Element) -> None:
    """Repair the bundled MathML converter's empty nary-body output.

    The converter emits ``m:nary`` with an empty ``m:e`` for sums.  Word may
    tolerate that, but LibreOffice displays empty square placeholders and the
    formula is not visually reliable.  Recasting the operator as an editable
    sub/superscripted sum preserves the visible mathematics and leaves the
    following expression as the operand.
    """
    for nary in list(math.xpath(".//m:nary", namespaces=NS)):
        body = nary.find(f"{M}e")
        if body is None or len(body) != 0 or (body.text or "").strip():
            continue
        nary_pr = nary.find(f"{M}naryPr")
        chr_node = nary_pr.find(f"{M}chr") if nary_pr is not None else None
        operator = chr_node.get(f"{M}val", "∑") if chr_node is not None else "∑"
        replacement = etree.Element(f"{M}sSubSup")
        etree.SubElement(replacement, f"{M}sSubSupPr")
        op_e = etree.SubElement(replacement, f"{M}e")
        op_run = etree.SubElement(op_e, f"{M}r")
        op_text = etree.SubElement(op_run, f"{M}t")
        op_text.text = operator
        for child_name in ("sub", "sup"):
            child = nary.find(f"{M}{child_name}")
            if child is not None:
                replacement.append(child)
        nary.getparent().replace(nary, replacement)


def first_run_properties(paragraph: etree._Element) -> etree._Element | None:
    run = paragraph.find(f".//{W}r")
    if run is None:
        return None
    props = run.find(f"{W}rPr")
    return etree.fromstring(etree.tostring(props)) if props is not None else None


def add_text_run(paragraph: etree._Element, text: str, run_props: etree._Element | None) -> None:
    if not text:
        return
    # Inline-math rebuilding reconstructs the paragraph's runs.  Preserve the
    # thesis citation convention while doing so; otherwise citations that share
    # a paragraph with an inline equation lose their superscript formatting.
    citation_re = re.compile(r"(\[(?:\d+(?:\s*[-,，]\s*\d+)*)\])")
    for part in citation_re.split(text):
        if not part:
            continue
        run = etree.SubElement(paragraph, f"{W}r")
        props = etree.fromstring(etree.tostring(run_props)) if run_props is not None else etree.Element(f"{W}rPr")
        if citation_re.fullmatch(part):
            vert_align = props.find(f"{W}vertAlign")
            if vert_align is None:
                vert_align = etree.SubElement(props, f"{W}vertAlign")
            vert_align.set(f"{W}val", "superscript")
        run.append(props)
        node = etree.SubElement(run, f"{W}t")
        if part[:1].isspace() or part[-1:].isspace():
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        node.text = part


def clear_paragraph_content(paragraph: etree._Element) -> None:
    ppr = paragraph.find(f"{W}pPr")
    for child in list(paragraph):
        if child is not ppr:
            paragraph.remove(child)


def set_center(paragraph: etree._Element) -> None:
    ppr = paragraph.find(f"{W}pPr")
    if ppr is None:
        ppr = etree.Element(f"{W}pPr")
        paragraph.insert(0, ppr)
    jc = ppr.find(f"{W}jc")
    if jc is None:
        jc = etree.SubElement(ppr, f"{W}jc")
    jc.set(f"{W}val", "center")


def append_math(paragraph: etree._Element, math: etree._Element, display: bool) -> None:
    if display:
        math_para = etree.Element(f"{M}oMathPara")
        math_para.append(math)
        paragraph.append(math_para)
    else:
        paragraph.append(math)


INLINE_RE = re.compile(r"\\\((.*?)\\\)|\\\[(.*?)\\\]", flags=re.S)

# The content backup predates the native-math conversion and contains a small
# number of inline expressions whose delimiters were stripped by the earlier
# Markdown-to-DOCX pass.  These are exact residual strings from the backup;
# code identifiers such as target_event and rule_trigger are intentionally not
# included because they are not mathematical expressions.
RAW_MATH = {
    "V=v_1,ldots,v_N\\": r"V=\{v_1,\ldots,v_N\}",
    "f_theta": r"f_\theta",
    "l_iinR^T": r"\mathbf{l}_i\in\mathbb{R}^{T}",
    "b_i=x^access_i+x^departure_i+|Deltax^active_i|": r"\mathbf{b}_i=\mathbf{x}^{\mathrm{access}}_i+\mathbf{x}^{\mathrm{departure}}_i+|\Delta\mathbf{x}^{\mathrm{active}}_i|",
    "p_iinR^96": r"\mathbf{p}_i\in\mathbb{R}^{96}",
    "max(mathbf A,mathbf A^mathsf T)": r"\max(\mathbf{A},\mathbf{A}^{\mathsf T})",
    "mathbf H^(0)inR^Btimes Ntimes D": r"\mathbf{H}^{(0)}\in\mathbb{R}^{B\times N\times D}",
    "mathbf W_r^(l)inR^Dtimes D": r"\mathbf{W}_r^{(l)}\in\mathbb{R}^{D\times D}",
    "boldsymbolbeta^(1)": r"\boldsymbol\beta^{(1)}",
    "boldsymbolbeta^(2)": r"\boldsymbol\beta^{(2)}",
    "boldsymbolbeta^(l)": r"\boldsymbol\beta^{(l)}",
    "boldsymbolbeta": r"\boldsymbol\beta",
    "mathbf H^(1,ref)": r"\mathbf{H}^{(1,\mathrm{ref})}",
    "mathbf H^(l-1)": r"\mathbf{H}^{(l-1)}",
    "mathbf H^(0)": r"\mathbf{H}^{(0)}",
    "mathbf H^(1)": r"\mathbf{H}^{(1)}",
    "mathbf H^(2)": r"\mathbf{H}^{(2)}",
    "H^(1,ref)": r"H^{(1,\mathrm{ref})}",
    "H^(0)": r"H^{(0)}",
    "H^(1)": r"H^{(1)}",
    "H^(2)": r"H^{(2)}",
    "mathbf a^(l)": r"\mathbf{a}^{(l)}",
    "mathbf G": r"\mathbf{G}",
    "mathbf H^(l)": r"\mathbf{H}^{(l)}",
    "10^-3": r"10^{-3}",
    "10^-4": r"10^{-4}",
    "10^-9": r"10^{-9}",
    "alpha=0.05": r"\alpha=0.05",
    "alpha=0.1": r"\alpha=0.1",
    "alpha=2.0": r"\alpha=2.0",
    "alphain\\0.1,0.5,1.0,2.0\\": r"\alpha\in\{0.1,0.5,1.0,2.0\}",
    "r=|y-hat y|": r"r=|y-\hat y|",
    "q_stable,n": r"q_{\mathrm{stable},n}",
    "q_trig": r"q_{\mathrm{trig}}",
    "q_n": r"q_n",
    "ASYM>0.3": r"\operatorname{ASYM}>0.3",
    "MAE(基线)-MAE(MRG-GCN)": r"\operatorname{MAE}(\text{基线})-\operatorname{MAE}(\text{MRG-GCN})",
}


def math_matches(text: str):
    matches = []
    for match in INLINE_RE.finditer(text):
        latex = match.group(1) if match.group(1) is not None else match.group(2)
        matches.append((match.start(), match.end(), latex.strip()))
    for raw, latex in sorted(RAW_MATH.items(), key=lambda item: len(item[0]), reverse=True):
        start = 0
        while True:
            pos = text.find(raw, start)
            if pos < 0:
                break
            matches.append((pos, pos + len(raw), latex))
            start = pos + len(raw)
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    selected = []
    for item in matches:
        if selected and item[0] < selected[-1][1]:
            continue
        selected.append(item)
    return selected


def replace_inline_math(root: etree._Element, converter, report: dict) -> None:
    for paragraph in root.xpath(".//w:p", namespaces=NS):
        text = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
        matches = math_matches(text)
        if not matches:
            continue
        props = first_run_properties(paragraph)
        clear_paragraph_content(paragraph)
        cursor = 0
        converted = 0
        for start, end, latex in matches:
            add_text_run(paragraph, text[cursor:start], props)
            try:
                append_math(paragraph, converter(latex.strip()), display=False)
                converted += 1
            except Exception as exc:
                add_text_run(paragraph, text[start:end], props)
                report["conversion_errors"].append({"kind": "inline", "latex": latex, "error": str(exc)})
            cursor = end
        add_text_run(paragraph, text[cursor:], props)
        report["inline_formulas"] += converted


def table_equation_tag(table: etree._Element) -> str | None:
    text = "".join(table.xpath(".//w:t/text()", namespaces=NS))
    match = re.search(r"[（(]([2-5]-\d+)[）)]", text)
    return match.group(1) if match else None


def equation_paragraph(
    number: str,
    math: etree._Element,
    number_props: etree._Element | None,
    *,
    text_width_twips: int = 8312,
) -> etree._Element:
    """Build a clean paragraph with centered native math and a right number.

    The previous draft used a three-column borderless table.  Word/WPS exposes
    the table gridlines in editing view, and fixed grid widths can clip long
    equations.  Tab stops provide the same visual alignment without a table.
    """
    paragraph = etree.Element(f"{W}p")
    ppr = etree.SubElement(paragraph, f"{W}pPr")
    spacing = etree.SubElement(ppr, f"{W}spacing")
    spacing.set(f"{W}before", "0")
    spacing.set(f"{W}after", "0")
    spacing.set(f"{W}line", "360")
    spacing.set(f"{W}lineRule", "atLeast")
    indent = etree.SubElement(ppr, f"{W}ind")
    indent.set(f"{W}firstLine", "0")
    indent.set(f"{W}left", "0")
    indent.set(f"{W}right", "0")
    jc = etree.SubElement(ppr, f"{W}jc")
    jc.set(f"{W}val", "left")
    # A4 page width is 11906 twips and the template's left/right margins are
    # 1797 twips each, so the usable text width is 8312 twips.  The previous
    # implementation used 4578/9156, which belonged to a wider layout and
    # pushed the equation number outside the current text area.
    tabs = etree.SubElement(ppr, f"{W}tabs")
    center_tab = etree.SubElement(tabs, f"{W}tab")
    center_tab.set(f"{W}val", "center")
    center_tab.set(f"{W}pos", str(text_width_twips // 2))
    right_tab = etree.SubElement(tabs, f"{W}tab")
    right_tab.set(f"{W}val", "right")
    right_tab.set(f"{W}pos", str(text_width_twips))

    tab_run = etree.SubElement(paragraph, f"{W}r")
    etree.SubElement(tab_run, f"{W}tab")
    paragraph.append(math)

    number_tab_run = etree.SubElement(paragraph, f"{W}r")
    etree.SubElement(number_tab_run, f"{W}tab")
    number_run = etree.SubElement(paragraph, f"{W}r")
    if number_props is not None:
        number_run.append(etree.fromstring(etree.tostring(number_props)))
    text = etree.SubElement(number_run, f"{W}t")
    text.text = number
    return paragraph


def replace_display_math(root: etree._Element, formulas: dict[str, str], converter, report: dict) -> None:
    for table in root.xpath(".//w:tbl", namespaces=NS):
        tag = table_equation_tag(table)
        if not tag or tag not in formulas:
            continue
        rows = table.xpath("./w:tr", namespaces=NS)
        if not rows:
            continue
        cells = rows[0].xpath("./w:tc", namespaces=NS)
        if len(cells) < 2:
            continue
        try:
            math = converter(formulas[tag])
            number_cell = cells[-1]
            number_props = first_run_properties(number_cell.xpath("./w:p", namespaces=NS)[0]) if number_cell.xpath("./w:p", namespaces=NS) else None
            number = "".join(number_cell.xpath(".//w:t/text()", namespaces=NS)).strip()
            paragraph = equation_paragraph(number, math, number_props)
            parent = table.getparent()
            if parent is None:
                continue
            parent.replace(table, paragraph)
            report["display_formulas"] += 1
            report["display_tags"].append(tag)
        except Exception as exc:
            report["conversion_errors"].append({"kind": "display", "tag": tag, "error": str(exc)})


def rebuild(source: Path, manuscript: Path, output: Path, node: str, converter: Path, node_path: str) -> dict:
    formulas = extract_tagged_formulas(manuscript.read_text(encoding="utf-8"))
    report = {
        "source": str(source.resolve()),
        "output": str(output.resolve()),
        "display_formulas": 0,
        "display_tags": [],
        "inline_formulas": 0,
        "conversion_errors": [],
    }
    with zipfile.ZipFile(source, "r") as zin:
        document = etree.fromstring(zin.read("word/document.xml"))

        def converter_fn(latex: str) -> etree._Element:
            return run_converter(latex, node, str(converter), node_path)

        # Numbered table equations first; inline formulas are then rebuilt in all
        # remaining paragraphs.  The two passes avoid touching equation numbers.
        replace_display_math(document, formulas, converter_fn, report)
        replace_inline_math(document, converter_fn, report)

        document_xml = etree.tostring(
            document, xml_declaration=True, encoding="UTF-8", standalone=True
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="formula-rebuild-", suffix=".docx", dir=output.parent, delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = document_xml if item.filename == "word/document.xml" else zin.read(item.filename)
                    zout.writestr(item, data)
            shutil.move(tmp_path, output)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    report["source_omml"] = 0
    report["output_omml"] = report["display_formulas"] + report["inline_formulas"]
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("manuscript", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--node", default="/Users/xushuyuan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
    parser.add_argument("--converter", type=Path, default=Path(__file__).with_name("latex_to_omml.js"))
    parser.add_argument("--node-path", default="/private/tmp/codex-thesis-math-runtime/node_modules")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = rebuild(args.source, args.manuscript, args.output, args.node, args.converter, args.node_path)
    args.report.write_text(__import__("json").dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(__import__("json").dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
