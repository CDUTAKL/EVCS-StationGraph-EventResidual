#!/usr/bin/env python3
"""Audit figure assets for publication-risk signals.

The audit is deliberately conservative: it reports signals for human review
and never declares a figure scientifically correct from pixels alone.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

FIG_DIR = Path("outputs/figures")
REPORT = Path("docs/thesis/figure-quality-audit-20260906.md")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
STEM_RE = re.compile(r"^(fig\d+_\d+)(?:_.+)?\.(png|svg)$")


def png_info(path: Path) -> dict:
    try:
        with Image.open(path) as im:
            dpi = im.info.get("dpi")
            return {"size": im.size, "dpi": dpi, "mode": im.mode}
    except Exception as exc:  # pragma: no cover - defensive audit path
        return {"error": str(exc)}


def svg_info(path: Path) -> dict:
    out = {"size": None, "font_sizes": [], "control_text": [], "text_count": 0}
    try:
        root = ET.parse(path).getroot()
        out["size"] = (root.attrib.get("width"), root.attrib.get("height"), root.attrib.get("viewBox"))
        for elem in root.iter():
            text = "".join(elem.itertext()) if elem.tag.endswith("text") else ""
            if text:
                out["text_count"] += 1
                if CONTROL_RE.search(text):
                    out["control_text"].append(text)
            style = elem.attrib.get("style", "")
            fs = elem.attrib.get("font-size")
            if fs is None:
                m = re.search(r"font-size\s*:\s*([0-9.]+)", style)
                fs = m.group(1) if m else None
            if fs is not None:
                try:
                    out["font_sizes"].append(float(re.sub(r"[^0-9.].*$", "", fs)))
                except ValueError:
                    pass
    except Exception as exc:  # pragma: no cover
        out["error"] = str(exc)
    return out


def main() -> None:
    pngs = sorted(FIG_DIR.glob("fig*.png"))
    svgs = sorted(FIG_DIR.glob("fig*.svg"))
    stems = sorted({p.stem for p in pngs + svgs})
    rows: list[str] = []
    rows.append("# 科研图片质量审计（2026-09-06）\n")
    rows.append("本报告是生成资产层面的风险筛查，不替代论文版心缩放后的人工目视审阅。\n")
    rows.append("## 汇总\n")
    rows.append(f"- PNG：{len(pngs)}；SVG：{len(svgs)}；唯一文件基名：{len(stems)}。")
    rows.append("- 重点风险信号：缺少矢量版、PNG无1200 DPI、SVG含控制字符、字体过小、PNG尺寸异常。\n")
    rows.append("## 逐图筛查\n")
    rows.append("| 图文件基名 | PNG | SVG | 分辨率/DPI | SVG文字/字号信号 | 初步处理建议 |")
    rows.append("|---|---|---|---|---|---|")
    for stem in stems:
        png = FIG_DIR / f"{stem}.png"
        svg = FIG_DIR / f"{stem}.svg"
        flags: list[str] = []
        ptext = "—"
        stext = "—"
        if png.exists():
            pi = png_info(png)
            if "error" in pi:
                flags.append("PNG读取失败")
                ptext = pi["error"]
            else:
                dpi = pi.get("dpi")
                ptext = f"{pi['size'][0]}×{pi['size'][1]}"
                if dpi:
                    ptext += f" @ {dpi[0]:.0f} dpi"
                else:
                    flags.append("PNG无DPI")
                if min(pi["size"]) < 1200:
                    flags.append("PNG像素偏小")
        else:
            flags.append("缺PNG")
        if svg.exists():
            si = svg_info(svg)
            stext = f"文本{si.get('text_count', 0)}"
            fs = si.get("font_sizes", [])
            if fs:
                stext += f"；字号{min(fs):g}–{max(fs):g}"
                if min(fs) < 6:
                    flags.append("SVG字号<6")
            if si.get("control_text"):
                flags.append("SVG控制字符")
            if si.get("error"):
                flags.append("SVG解析失败")
        else:
            flags.append("缺SVG")
        if not flags:
            suggestion = "通过资产层筛查；仍需版心缩放目视复核"
        elif set(flags) <= {"PNG无DPI", "缺SVG"}:
            suggestion = "优先补矢量版并统一PNG导出"
        else:
            suggestion = "进入人工目视复核/重绘队列"
        rows.append(f"| `{stem}` | {ptext} | {stext} | {'、'.join(flags) or '无'} | {suggestion} |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
