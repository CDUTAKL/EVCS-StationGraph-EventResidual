#!/usr/bin/env python3
"""Build editable draw.io sources and thesis exports for five revised diagrams.

The YAML specs are the canonical diagram sources. Run this module from the
repository root; it uses the drawio-academic-skills CLI and the local draw.io
Desktop renderer for PNG exports embedded in the thesis.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "outputs/figures"
SPECS = FIG / "diagram_sources"
CLI = Path.home() / ".codex/skills/drawio/scripts/cli.js"

BLUE = "#2C5F8A"
BLUE_FILL = "#E8EFF3"
BLUE_LINE = "#56798E"
WARM_FILL = "#F2EAE3"
WARM_LINE = "#A08B7D"
GOLD_FILL = "#FBF5E9"
GOLD_LINE = "#B39A61"
GRAY_FILL = "#F3F5F6"
GRAY_LINE = "#BAC2C7"
INK = "#303C44"
GRAY = "#858D92"
NOTE = "#68757D"
WHITE = "#FFFFFF"


def _node(nid: str, label: str, kind: str, bounds: tuple[int, int, int, int],
          fill: str | None, stroke: str | None, size: int = 18,
          *, color: str = INK, align: str = "center", bold: bool = False,
          radius: bool = True) -> dict:
    style = {"fontColor": color, "fontSize": max(8, min(10, size)),
             "align": align, "verticalAlign": "middle",
             "fontStyle": 1 if bold else 0, "rounded": radius}
    if fill:
        style["fillColor"] = fill
    if stroke:
        style["strokeColor"] = stroke
    return {"id": nid, "label": label, "type": kind, "bounds": bounds,
            "style": style}


def _edge(source: str, target: str, *, label: str = "", kind: str = "primary",
          color: str = BLUE_LINE, dashed: bool = False,
          waypoints: list[tuple[int, int]] | None = None,
          width: int = 2, label_offset: tuple[int, int] | None = None) -> dict:
    item = {"from": source, "to": target, "type": kind,
            "style": {"strokeColor": color, "strokeWidth": width}}
    if label:
        item["label"] = label
        if label_offset:
            item["labelOffset"] = {"x": label_offset[0], "y": label_offset[1]}
    if dashed:
        item["style"]["dashed"] = True
        item["style"]["dashPattern"] = "7 4"
    if waypoints:
        item["waypoints"] = [{"x": x, "y": y} for x, y in waypoints]
    return item


def _spec(name: str, title: str, description: str, width: int, height: int,
          figure_type: str, nodes: list[dict], edges: list[dict],
          legend: str = "实线表示流程；虚线表示冻结参数或验证信息。") -> Path:
    meta = {
        "profile": "academic-paper", "figureType": figure_type,
        "source": "edited", "theme": "academic-color", "layout": "horizontal",
        "canvas": f"{width}x{height}", "routing": "orthogonal",
        "title": title, "description": description, "legend": legend,
        "font": {"primary": "Times New Roman", "cjk": "Songti SC",
                 "formula": "Times New Roman"},
        "replication": {
            "colorMode": "preserve-original", "background": WHITE,
            "palette": [
                {"hex": BLUE_FILL, "role": "主体流程节点填充", "appliesTo": "nodes", "confidence": "high"},
                {"hex": WARM_FILL, "role": "数据与结果节点填充", "appliesTo": "nodes", "confidence": "high"},
                {"hex": GOLD_FILL, "role": "判断节点填充", "appliesTo": "nodes", "confidence": "high"},
                {"hex": BLUE_LINE, "role": "主流程连线", "appliesTo": "edges", "confidence": "high"},
            ],
            "confidenceNotes": ["保留论文蓝灰、暖灰色彩语义；重画节点、箭头与文字，不沿用旧图的像素几何。"],
        },
    }
    out = ["meta:"]
    for k, v in meta.items():
        if k == "font":
            out.extend(["  font:", f"    primary: {json.dumps(v['primary'])}",
                        f"    cjk: {json.dumps(v['cjk'])}",
                        f"    formula: {json.dumps(v['formula'])}"])
        elif k == "replication":
            out.extend(["  replication:", f"    colorMode: {v['colorMode']}",
                         f"    background: {json.dumps(v['background'])}", "    palette:"])
            for p in v["palette"]:
                out.extend([f"      - hex: {json.dumps(p['hex'])}",
                            f"        role: {json.dumps(p['role'], ensure_ascii=False)}",
                            f"        appliesTo: {p['appliesTo']}",
                            f"        confidence: {p['confidence']}"])
            out.append("    confidenceNotes:")
            out.append(f"      - {json.dumps(v['confidenceNotes'][0], ensure_ascii=False)}")
        else:
            out.append(f"  {k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, str) else v}")
    out.append("\nnodes:")
    for n in nodes:
        out.extend([f"  - id: {n['id']}",
                    f"    label: {json.dumps(n['label'], ensure_ascii=False)}",
                    f"    type: {n['type']}",
                    "    bounds: { x: %d, y: %d, width: %d, height: %d }" % n["bounds"],
                    "    style:"])
        for attr in ("fillColor", "strokeColor", "fontColor"):
            if attr in n["style"]:
                out.append(f"      {attr}: {json.dumps(n['style'][attr])}")
        out.extend([f"      fontSize: {n['style']['fontSize']}",
                    f"      fontStyle: {n['style']['fontStyle']}",
                    f"      rounded: {'true' if n['style']['rounded'] else 'false'}",
                    f"      align: {n['style']['align']}",
                    "      verticalAlign: middle"])
    out.append("\nedges:")
    for e in edges:
        out.extend([f"  - from: {e['from']}", f"    to: {e['to']}",
                    f"    type: {e['type']}"])
        if e.get("label"):
            out.append(f"    label: {json.dumps(e['label'], ensure_ascii=False)}")
        if e.get("labelOffset"):
            out.extend(["    labelOffset:", f"      x: {e['labelOffset']['x']}",
                        f"      y: {e['labelOffset']['y']}"])
        if e.get("waypoints"):
            out.append("    waypoints:")
            for p in e["waypoints"]:
                out.append(f"      - x: {p['x']}")
                out.append(f"        y: {p['y']}")
        out.append("    style:")
        for attr in ("strokeColor", "strokeWidth"):
            out.append(f"      {attr}: {json.dumps(e['style'][attr]) if isinstance(e['style'][attr], str) else e['style'][attr]}")
        if e["style"].get("dashed"):
            out.append("      dashed: true")
            out.append(f"      dashPattern: {json.dumps(e['style']['dashPattern'])}")
    SPECS.mkdir(parents=True, exist_ok=True)
    path = SPECS / f"{name}.spec.yaml"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def _build_specs() -> list[Path]:
    specs: list[Path] = []

    # Figure 2-7: score construction, threshold fitting and rule execution are
    # separate stages. The validation quantile enters the decision from above;
    # the positive and negative outcomes leave the decision independently.
    n = [
        _node("title", "冻结规则事件窗口：分数、阈值与执行", "text", (40, 18, 920, 34), None, None, 22, align="left", bold=True),
        _node("scope", "训练段估计逐节点标准差；验证段冻结非零分数95%分位阈值；测试段只应用规则", "text", (42, 55, 915, 28), None, None, 15, color=NOTE, align="left"),
        _node("signals", "接入数 · 离站数\n|活跃变化| · |负荷变化|", "process", (42, 120, 260, 80), BLUE_FILL, BLUE_LINE, 18),
        _node("scale", "逐节点标准差归一化\nσ 仅由训练段估计", "process", (42, 230, 260, 76), BLUE_FILL, BLUE_LINE, 18),
        _node("score", "四分量求和\n当前分数 q(t,i)", "process", (42, 340, 260, 76), BLUE_FILL, BLUE_LINE, 18),
        _node("val", "验证段：筛选 q(t,i)>0", "process", (370, 120, 260, 80), WARM_FILL, WARM_LINE, 18),
        _node("quantile", "逐节点计算95%分位数", "process", (370, 230, 260, 76), BLUE_FILL, BLUE_LINE, 18),
        _node("threshold", "冻结阈值 θᵢ", "terminal", (370, 340, 260, 76), WARM_FILL, WARM_LINE, 18, bold=True),
        _node("compare", "q(t,i) > θᵢ ?", "decision", (420, 470, 160, 100), GOLD_FILL, GOLD_LINE, 19, bold=True),
        _node("trigger", "是：记录触发点 t\n并向未来扩展2步", "process", (105, 635, 330, 70), BLUE_FILL, BLUE_LINE, 17),
        _node("no_trigger", "否：该起点不触发", "process", (585, 635, 310, 70), GRAY_FILL, GRAY_LINE, 17),
        _node("windows", "合并段内相邻或重叠窗口\n输出冻结规则事件窗口", "terminal", (105, 750, 420, 68), WARM_FILL, WARM_LINE, 17, bold=True),
    ]
    e = [
        _edge("signals", "scale"), _edge("scale", "score"),
        _edge("val", "quantile"), _edge("quantile", "threshold"),
        _edge("score", "compare", label="当前 q(t,i)",
              waypoints=[(175, 438), (350, 438), (350, 520)], label_offset=(0, -12)),
        _edge("threshold", "compare", kind="data", color=WARM_LINE, dashed=True,
              label="冻结 θᵢ", label_offset=(18, 0)),
        _edge("compare", "trigger", label="是", color=BLUE,
              waypoints=[(500, 600), (270, 600)], label_offset=(0, -12)),
        _edge("compare", "no_trigger", label="否", color=GRAY,
              waypoints=[(500, 600), (740, 600)], label_offset=(0, -12)),
        _edge("trigger", "windows", color=BLUE),
    ]
    specs.append(_spec("fig2_7_event_score_flow", "事件分数与冻结规则事件窗口生成流程",
                       "训练标准差、验证阈值冻结和逐点规则执行的审计流程。",
                       1000, 840, "workflow", n, e,
                       "实线为分数或规则流程；虚线表示由验证段确定并冻结的阈值输入。"))

    # Figure 3-8: validation patience continues the current run; the loop never
    # returns to preprocessing or begins a new seed. Best validation weights
    # are restored before test inference.
    n = [
        _node("title", "训练、检查点选择与测试评价流程", "text", (40, 16, 920, 36), None, None, 22, align="left", bold=True),
        _node("split", "固定时间切分\n合法预测起点", "process", (390, 66, 220, 62), GRAY_FILL, GRAY_LINE, 18, bold=True),
        _node("train_set", "训练集\n83,103", "process", (45, 168, 245, 70), BLUE_FILL, BLUE_LINE, 18),
        _node("val_set", "验证集\n17,807", "process", (377, 168, 245, 70), WARM_FILL, WARM_LINE, 18),
        _node("test_set", "测试集\n17,809", "process", (710, 168, 245, 70), GRAY_FILL, GRAY_LINE, 18),
        _node("scale", "仅训练段拟合归一化参数\n相同变换用于验证和测试", "process", (45, 278, 245, 76), BLUE_FILL, BLUE_LINE, 16),
        _node("windows", "96步历史 → 4步目标\n滑动预测窗口", "process", (45, 390, 245, 76), BLUE_FILL, BLUE_LINE, 17),
        _node("epoch", "每个种子训练一轮\n2024 · 2025 · 2026", "process", (365, 282, 235, 76), BLUE_FILL, BLUE_LINE, 17),
        _node("val_mae", "验证 MAE\n更新最优检查点与耐心计数", "process", (365, 392, 235, 76), WARM_FILL, WARM_LINE, 16),
        _node("stop", "连续8轮无改进\n或达到60轮?", "decision", (385, 500, 195, 100), GOLD_FILL, GOLD_LINE, 17, bold=True),
        _node("best", "恢复该种子\n验证 MAE 最优权重", "terminal", (710, 528, 245, 70), WARM_FILL, WARM_LINE, 16, bold=True),
        _node("infer", "测试集前向推理\n直接输出未来4步", "process", (710, 285, 245, 76), BLUE_FILL, BLUE_LINE, 17),
        _node("eval", "按统一预测键评价\n全局 · 分层 · 节点 · 步长", "terminal", (710, 402, 245, 80), WARM_FILL, WARM_LINE, 16, bold=True),
        _node("scope", "“否”回到同一训练运行的下一轮；验证用于早停与选点，测试只作最终评价。", "text", (48, 670, 910, 28), None, None, 15, color=NOTE, align="left"),
    ]
    e = [
        _edge("split", "train_set", waypoints=[(500, 146), (168, 146)]),
        _edge("split", "val_set"),
        _edge("split", "test_set", waypoints=[(500, 146), (832, 146)]),
        _edge("train_set", "scale"), _edge("scale", "windows"),
        _edge("windows", "epoch", waypoints=[(325, 428), (325, 320)]),
        _edge("val_set", "val_mae", kind="data", color=WARM_LINE, dashed=True,
              waypoints=[(655, 203), (655, 430)]),
        _edge("epoch", "val_mae"), _edge("val_mae", "stop"),
        _edge("stop", "epoch", label="否：下一轮", color=BLUE,
              waypoints=[(335, 550), (335, 320)], label_offset=(-10, -14)),
        _edge("stop", "best", label="是：停止", color=WARM_LINE,
              waypoints=[(635, 550)], label_offset=(0, -14)),
        _edge("test_set", "infer", kind="data", color=GRAY, dashed=True),
        _edge("best", "infer", kind="data", color=WARM_LINE, dashed=True,
              waypoints=[(975, 563), (975, 323)]),
        _edge("infer", "eval"),
    ]
    specs.append(_spec("fig3_8_train_predict_pipeline", "训练—预测—评价流程",
                       "保持训练、验证与测试分工，并明确同一运行内的早停反馈。",
                       1000, 720, "workflow", n, e,
                       "实线表示训练和推理；虚线表示验证或冻结检查点信息。"))

    # Figure 4-1: each MDP layer has its own question-method-evidence-conclusion
    # chain. No evidence path is allowed to terminate in another layer.
    xs = [35, 145, 325, 565, 785]
    ws = [90, 160, 220, 200, 180]
    headers = ["层级", "诊断问题", "操作", "关键证据", "判定边界"]
    n = [_node("title", "三层机制诊断协议（MDP）", "text", (35, 16, 930, 34), None, None, 22, align="left", bold=True),
         _node("sub", "每一层的操作、证据和结论逐行对应", "text", (36, 52, 920, 24), None, None, 15, color=NOTE, align="left")]
    for j, (x, w, h) in enumerate(zip(xs, ws, headers)):
        n.append(_node(f"h{j}", h, "text", (x, 102, w, 34), None, None, 15, color=NOTE, bold=True))

    rows = [
        ("L1\n干预归因", "关系级 β 分配\n是否有功能依赖？",
         "观察两层 β\n冻结权重前向干预\n7种配置 × 3种子",
         "7/7干预均退化\nMAE +95.9%–+233.6%",
         "支持所检关系权重\n存在功能依赖"),
        ("L2\n蒸馏验证", "所检时序学生能否\n吸收图模型知识？",
         "StaticGraph 教师\n→ TCN 学生\n4个权重 × 3种子",
         "TCN MAE ≈ 0.029\n教师 0.01376\n所检设置未弥合差距",
         "结论限于所检学生、\n蒸馏目标与权重范围"),
        ("L3\n四格溯源", "不同窗口如何贡献\n全局预测误差？",
         "target_event × rule_trigger\n四格分层；按样本量加权",
         "四格加权 MAE\n还原全局 MAE\n事件格误差约为稳定格28倍",
         "定位误差来源；\n不作因果解释"),
    ]
    yrows = [150, 316, 482]
    edges: list[dict] = []
    for ridx, (y, row) in enumerate(zip(yrows, rows)):
        layer, question, method, evidence, conclusion = row
        fill = [BLUE_FILL, GRAY_FILL, WARM_FILL, BLUE_FILL, WARM_FILL]
        line = [BLUE_LINE, GRAY_LINE, BLUE_LINE, BLUE_LINE, WARM_LINE]
        labels = [layer, question, method, evidence, conclusion]
        for cidx, (x, w, label) in enumerate(zip(xs, ws, labels)):
            n.append(_node(f"r{ridx}c{cidx}", label,
                           "terminal" if cidx == 0 or cidx == 4 else "process",
                           (x, y, w, 120), fill[cidx], line[cidx],
                           15 if cidx != 0 else 16, bold=(cidx == 0 or cidx == 4)))
        for cidx in range(1, 4):
            edges.append(_edge(f"r{ridx}c{cidx}", f"r{ridx}c{cidx+1}",
                               color=BLUE_LINE if cidx < 3 else WARM_LINE, width=1))
    n.append(_node("boundary", "共同边界：旧 Caltech 主协议；L2结论仅适用于图示的学生架构、蒸馏目标和权重范围。",
                   "text", (40, 655, 920, 34), None, None, 15, color=NOTE, align="left"))
    specs.append(_spec("fig4_1_three_layer_framework", "三层机制诊断协议（MDP）",
                       "按L1干预归因、L2蒸馏验证和L3四格溯源呈现逐层证据与判定边界。",
                       1000, 710, "workflow", n, edges,
                       "横向箭头只连接同一行的诊断问题、操作、证据与判定。"))

    # Figure 5-1: TE and PCMCI+ both receive the full training sequence. The
    # comparison is performed over all inter-node directed pairs, so PCMCI-only
    # pairs remain representable and the 44/76 figure is not called replication.
    n = [
        _node("title", "TE候选生成与PCMCI+条件独立核验", "text", (40, 18, 920, 34), None, None, 22, align="left", bold=True),
        _node("input", "同一训练段\n10节点负荷序列", "terminal", (35, 230, 205, 95), WARM_FILL, WARM_LINE, 18, bold=True),
        _node("te", "传递熵（TE）筛选\n8分位分箱 · 滞后1/2/4\n100次循环平移置换", "process", (310, 105, 280, 105), BLUE_FILL, BLUE_LINE, 17),
        _node("pcmci", "PCMCI+ 条件独立检验\n完整训练序列输入\nParCorr · 最大滞后4\n名义 α = 0.05", "process", (310, 355, 280, 115), GRAY_FILL, GRAY_LINE, 16),
        _node("te_out", "76 / 90\n名义TE候选有向对", "terminal", (675, 105, 270, 90), WARM_FILL, WARM_LINE, 18, bold=True),
        _node("pcmci_out", "80 条名义显著滞后\n再按有向节点对去重", "terminal", (675, 365, 270, 90), BLUE_FILL, BLUE_LINE, 17, bold=True),
        _node("compare", "在全部90个节点间有向对上逐对对照\n44/76 同时达阈值 · 32 未达PCMCI+阈值\n另有6个仅PCMCI+达到阈值的节点间对", "process", (280, 525, 600, 105), BLUE_FILL, BLUE_LINE, 17, bold=True),
        _node("caveat", "同一训练序列上的方法交叉核验，不是独立数据复现；未作多重比较校正，不解释为物理因果。",
               "text", (42, 665, 915, 26), None, None, 14, color=NOTE, align="left"),
    ]
    e = [
        _edge("input", "te", waypoints=[(260, 275), (260, 158)]),
        _edge("input", "pcmci", waypoints=[(260, 275), (260, 412)]),
        _edge("te", "te_out"), _edge("pcmci", "pcmci_out"),
        _edge("te_out", "compare", waypoints=[(810, 230), (810, 505)]),
        _edge("pcmci_out", "compare"),
    ]
    specs.append(_spec("fig5_1_te_pcmci_flow", "TE候选与PCMCI+条件独立核验流程",
                       "两个检验共享完整训练序列，输出按有向节点对汇总并比较。",
                       1000, 710, "workflow", n, e,
                       "主线表示两项检验共享训练数据；图中的44/76表示同序列上的方法一致性。"))

    # Figure 3-7 is a model architecture rather than a procedural flowchart.
    # H(1,ref) feeds GCN2 only; the skip fusion receives H0, H1 and H2.
    n = [
        _node("title", "跨层表示与预测头", "text", (35, 16, 930, 34), None, None, 22, align="left", bold=True),
        _node("h0", "H⁽⁰⁾\n[B,N,32]", "process", (35, 140, 120, 78), WARM_FILL, WARM_LINE, 17, bold=True),
        _node("gcn1", "第一层\n多关系传播", "process", (195, 140, 145, 78), BLUE_FILL, BLUE_LINE, 17),
        _node("h1", "H⁽¹⁾\n[B,N,32]", "process", (380, 140, 120, 78), BLUE_FILL, BLUE_LINE, 17, bold=True),
        _node("refine", "残差 MLP\n精炼", "process", (535, 140, 145, 78), WARM_FILL, WARM_LINE, 17),
        _node("href", "H⁽¹,ref⁾\n[B,N,32]", "process", (710, 140, 135, 78), WARM_FILL, WARM_LINE, 16, bold=True),
        _node("gcn2", "第二层\n多关系传播", "process", (880, 140, 115, 78), BLUE_FILL, BLUE_LINE, 16),
        _node("h2", "H⁽²⁾\n[B,N,32]", "process", (880, 260, 115, 72), BLUE_FILL, BLUE_LINE, 16, bold=True),
        _node("concat", "跨层拼接\n[H⁽⁰⁾ ∥ H⁽¹⁾ ∥ H⁽²⁾]\n[B,N,96]", "process", (225, 435, 245, 110), BLUE_FILL, BLUE_LINE, 18, bold=True),
        _node("fusion", "融合映射\nLinear · LayerNorm\nGELU · Dropout", "process", (525, 435, 205, 110), GRAY_FILL, GRAY_LINE, 16),
        _node("head", "预测头\nLinear", "process", (780, 435, 150, 110), WARM_FILL, WARM_LINE, 17),
        _node("output", "Ŷ\n[B,4,10]", "terminal", (780, 605, 150, 62), WARM_FILL, WARM_LINE, 17, bold=True),
        _node("note", "精炼状态只进入第二层传播；跨层拼接只接收三层原始状态。", "text", (35, 690, 925, 27), None, None, 15, color=NOTE, align="left"),
    ]
    e = [
        _edge("h0", "gcn1"), _edge("gcn1", "h1"), _edge("h1", "refine"),
        _edge("refine", "href", color=WARM_LINE),
        _edge("href", "gcn2", color=WARM_LINE), _edge("gcn2", "h2"),
        _edge("h0", "concat", waypoints=[(95, 365), (275, 365)]),
        _edge("h1", "concat", waypoints=[(440, 365), (365, 365)]),
        _edge("h2", "concat", waypoints=[(937, 375), (495, 375)]),
        _edge("concat", "fusion"), _edge("fusion", "head"), _edge("head", "output"),
    ]
    specs.append(_spec("fig3_7_cross_layer_detail", "跨层表示路径与预测头",
                       "显示两层传播、残差精炼的输入关系及跨层拼接内容。",
                       1020, 750, "architecture", n, e,
                       "箭头表示张量传递；跨层拼接不含精炼状态H⁽¹,ref⁾。"))
    return specs


def _run_cli(spec: Path, name: str, extension: str, *, desktop: bool) -> None:
    if not CLI.is_file():
        raise FileNotFoundError(f"draw.io academic CLI not found: {CLI}")
    output = FIG / f"{name}.{extension}"
    sidecar_dir = SPECS / f"{name}.sidecars"
    command = ["node", str(CLI), str(spec), str(output), "--validate",
               "--strict-warnings", "--write-sidecars", "--sidecar-dir", str(sidecar_dir)]
    if desktop:
        command.append("--use-desktop")
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"draw.io export failed for {name}.{extension}:\n{result.stdout}\n{result.stderr}")
    print(result.stdout.strip())


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    specs = _build_specs()
    for spec in specs:
        name = spec.name.removesuffix(".spec.yaml")
        _run_cli(spec, name, "drawio", desktop=False)
        _run_cli(spec, name, "svg", desktop=False)
        _run_cli(spec, name, "png", desktop=True)
    print(f"Generated {len(specs)} editable academic diagrams and SVG/PNG exports.")


if __name__ == "__main__":
    main()
