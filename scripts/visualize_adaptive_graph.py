from __future__ import annotations

"""自适应图可视化脚本：回答"自适应图学到了什么"。

本脚本读取 SG-EXP-004（AdaptiveGraph）的夜间训练产物与重训练日志，产出：
1. 四联热力图（load / event / pattern / 自适应混合邻接）；
2. 三种子固定图权重 α = sigmoid(fixed_weight) 的训练曲线；
3. 自适应混合邻接 top-10 边及其在固定关系中的排名 JSON。

所有路径默认值均指向工作目录下的已有产物；可通过命令行参数覆盖。
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

# 尝试引入项目既定可视化 Skill 的辅助函数；失败时降级为本地实现。
_SKILL_DIR = os.path.expanduser("~/.codex/skills/scipilot-figure-skill/scripts")
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)

try:
    from setup_style import setup_style  # type: ignore
    from export_figure import export_figure  # type: ignore
    _HAS_SCIPILOT = True
except Exception:  # pragma: no cover - 环境未安装 Skill 时降级
    setup_style = None  # type: ignore
    export_figure = None  # type: ignore
    _HAS_SCIPILOT = False


SEEDS: Tuple[int, int, int] = (2024, 2025, 2026)
DEFAULT_NIGHT_RUN_DIR = (
    "outputs/night_run/20260730-171821/SG-EXP-004/20260730-171821"
)
DEFAULT_RETRAINED_DIR = "outputs/experiments/SG-EXP-004/20260731-102456"
DEFAULT_NODE_LIST = "data/processed/SG-DATA-003-primary-node-list.csv"
DEFAULT_OUTPUT_DIR = "outputs/figures"
DEFAULT_ANALYSIS_DIR = "outputs/analysis"

# 与模型源码 _build_adaptive_adjacency 保持一致的数值容差。
_EPS = 1e-12


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="可视化 SG-EXP-004 自适应图所学到的邻接结构。"
    )
    parser.add_argument(
        "--night-run-dir",
        default=DEFAULT_NIGHT_RUN_DIR,
        help="夜间训练产物目录，需含 relation_matrices.npz 与 seed-*/model.pt。",
    )
    parser.add_argument(
        "--retrained-dir",
        default=DEFAULT_RETRAINED_DIR,
        help="重训练版日志目录，需含 seed-*/training_log.csv（含 adaptive_graph_alpha 列）。",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2024,
        choices=SEEDS,
        help="热力图默认使用的随机种子。",
    )
    parser.add_argument(
        "--node-list",
        default=DEFAULT_NODE_LIST,
        help="节点清单 CSV，第一列为 node_id。",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="图片输出目录。",
    )
    parser.add_argument(
        "--analysis-dir",
        default=DEFAULT_ANALYSIS_DIR,
        help="分析 JSON 输出目录。",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=1200,
        help="输出 PNG 的 DPI。",
    )
    return parser.parse_args()


def _require_file(path: str) -> str:
    """检查文件存在；不存在时显式失败，避免静默跳过。"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"缺失必需文件：{path}")
    return path


def load_node_list(path: str) -> List[str]:
    """读取节点清单，返回 node_id 列表。"""
    _require_file(path)
    df = pd.read_csv(path)
    if "node_id" not in df.columns:
        raise ValueError(f"节点清单 {path} 缺少 'node_id' 列")
    return df["node_id"].astype(str).tolist()


def load_fixed_relations(path: str) -> Dict[str, np.ndarray]:
    """读取三类固定关系矩阵。"""
    _require_file(path)
    with np.load(path) as data:
        relations = {key: np.asarray(data[key], dtype=np.float32) for key in data.keys()}
    expected = {"load", "event", "pattern"}
    missing = expected - set(relations.keys())
    if missing:
        raise ValueError(f"关系矩阵文件 {path} 缺少键：{missing}")
    return relations


def load_model_state(night_run_dir: str, seed: int) -> Dict[str, torch.Tensor]:
    """加载指定种子的 model.pt，返回 model_state 字典。"""
    path = os.path.join(night_run_dir, f"seed-{seed}", "model.pt")
    _require_file(path)
    # weights_only=True 限制反序列化范围，降低任意代码执行风险；
    # checkpoint 仅含张量与标量字典，兼容安全加载模式。
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if "model_state" not in checkpoint:
        raise ValueError(f"checkpoint {path} 缺少 'model_state' 键")
    return checkpoint["model_state"]


def _build_adaptive_adjacency(
    source_embedding: np.ndarray,
    target_embedding: np.ndarray,
    fixed_weight: float,
    fixed_adjs: List[np.ndarray],
    top_k: int,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """复现 graph.py 中 _build_adaptive_adjacency，使用 PyTorch 算子保证数值一致。

    返回三元组：
      - A_adp：自适应邻接矩阵（已归一化）。
      - A_mix：α·mean(A_fixed) + (1-α)·A_adp 的混合矩阵。
      - alpha：sigmoid(fixed_weight) 的标量值。
    """
    num_nodes = source_embedding.shape[0]
    embed_dim = source_embedding.shape[1]

    # 缩放点积注意力：E_s @ E_t^T / sqrt(d_e)。
    source_t = torch.from_numpy(source_embedding)
    target_t = torch.from_numpy(target_embedding)
    scale = float(embed_dim) ** 0.5
    logits = source_t @ target_t.T / scale

    # ReLU + Softmax 逐行归一化；随后屏蔽对角线并做 top-k 稀疏化。
    learned = torch.softmax(torch.relu(logits), dim=-1)
    self_mask = torch.eye(num_nodes, dtype=torch.bool)
    learned = learned.masked_fill(self_mask, float("-inf"))
    top_k_eff = min(int(top_k), num_nodes - 1)
    topk_vals, topk_idx = torch.topk(learned, k=top_k_eff, dim=-1)
    sparse = torch.zeros_like(learned).scatter(-1, topk_idx, topk_vals)

    # 对称化 + 自环 + 归一化（与模型源码一致，全部为非 in-place 操作）。
    sparse = (sparse + sparse.T) / 2.0
    sparse = sparse.masked_fill(self_mask, 1.0)
    deg = sparse.sum(dim=-1).pow(-0.5).clamp(min=_EPS)
    adaptive = deg.unsqueeze(-1) * sparse * deg.unsqueeze(-2)
    adaptive_np = adaptive.numpy()

    # α = sigmoid(fixed_weight)，再与固定图均值做加权混合。
    alpha = float(torch.sigmoid(torch.tensor(fixed_weight)).item())
    fixed_avg = np.mean(np.stack(fixed_adjs, axis=0), axis=0)
    mixed = alpha * fixed_avg + (1.0 - alpha) * adaptive_np
    return adaptive_np, mixed, alpha


def _setup_publication_style(lang: str = "zh") -> None:
    """配置出版级 matplotlib 样式；Skill 不可用时使用本地兜底。"""
    if setup_style is not None:
        try:
            setup_style(journal="nature", lang=lang)
            return
        except Exception:
            pass  # 降级到本地兜底，通常由 CJK 字体缺失触发。

    # 本地兜底：启用 tight layout，关闭上/右边框，配置可用中文字体。
    plt.rcParams.update(
        {
            "font.size": 7,
            "axes.labelsize": 8,
            "axes.titlesize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "lines.linewidth": 1.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "figure.dpi": 150,
            "savefig.dpi": 300,
        }
    )
    if lang == "zh":
        # 按常见 macOS / Linux 中文字体做兜底匹配，避免豆腐块。
        candidates = [
            "PingFang SC",
            "Heiti SC",
            "STHeiti",
            "Heiti TC",
            "Arial Unicode MS",
            "WenQuanYi Zen Hei",
            "DejaVu Sans",
        ]
        available = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
        chosen = next((c for c in candidates if c in available), None)
        if chosen is not None:
            plt.rcParams["font.family"] = ["sans-serif"]
            plt.rcParams["font.sans-serif"] = [chosen, "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False


def _draw_single_heatmap(
    ax: plt.Axes,
    matrix: np.ndarray,
    node_ids: List[str],
    title: str,
    vmin: float,
    vmax: float,
    cmap: str = "cividis",
) -> matplotlib.colorbar.Colorbar:
    """绘制单张热力图并返回 colorbar 对象。"""
    im = ax.imshow(
        matrix,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        aspect="equal",
    )
    ax.set_xticks(np.arange(len(node_ids)))
    ax.set_yticks(np.arange(len(node_ids)))
    ax.set_xticklabels(node_ids, rotation=45, ha="right")
    ax.set_yticklabels(node_ids)
    ax.set_title(title, pad=8)
    # 主网格线辅助阅读节点边界。
    for pos in np.arange(-0.5, len(node_ids), 1.0):
        ax.axhline(pos, color="white", linewidth=0.5)
        ax.axvline(pos, color="white", linewidth=0.5)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Edge weight")
    return cbar


def plot_heatmaps(
    night_run_dir: str,
    seed: int,
    node_ids: List[str],
    output_dir: str,
    dpi: int,
) -> str:
    """绘制并导出四联热力图。"""
    relations = load_fixed_relations(os.path.join(night_run_dir, "relation_matrices.npz"))
    state = load_model_state(night_run_dir, seed)
    fixed_adjs = [relations["load"], relations["event"], relations["pattern"]]
    adaptive, mixed, alpha = _build_adaptive_adjacency(
        source_embedding=state["source_embedding"].numpy(),
        target_embedding=state["target_embedding"].numpy(),
        fixed_weight=state["fixed_weight"].item(),
        fixed_adjs=fixed_adjs,
        top_k=5,
    )

    matrices = {
        "Load": relations["load"],
        "Event": relations["event"],
        "Pattern": relations["pattern"],
        f"Mixed ($\\alpha={alpha:.3f}$)": mixed,
    }
    # 统一色标：以四张图全局最大值为上界，0 为下界（邻接权重非负）。
    vmax = max(np.max(m) for m in matrices.values())
    vmin = 0.0

    _setup_publication_style(lang="zh")
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(7.2, 6.5),
        constrained_layout=True,
    )
    for ax, (title, mat) in zip(axes.flat, matrices.items()):
        _draw_single_heatmap(ax, mat, node_ids, title, vmin, vmax)

    basename = os.path.join(output_dir, "fig_adaptive_graph_heatmaps")
    if export_figure is not None:
        export_figure(
            fig,
            basename=basename,
            formats=["png", "pdf"],
            dpi=dpi,
            size_inches=(7.2, 6.5),
            tight=True,
            pad_inches=0.02,
        )
    else:
        os.makedirs(output_dir, exist_ok=True)
        fig.savefig(f"{basename}.png", dpi=dpi, bbox_inches="tight", pad_inches=0.02)
        fig.savefig(f"{basename}.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return f"{basename}.png"


def _load_alpha_curves(retrained_dir: str) -> Dict[int, pd.DataFrame]:
    """读取三种子的 training_log.csv，返回 {seed: DataFrame}。"""
    out: Dict[int, pd.DataFrame] = {}
    for seed in SEEDS:
        path = os.path.join(retrained_dir, f"seed-{seed}", "training_log.csv")
        _require_file(path)
        df = pd.read_csv(path)
        if "adaptive_graph_alpha" not in df.columns:
            raise ValueError(f"{path} 缺少 'adaptive_graph_alpha' 列")
        if "epoch" not in df.columns:
            raise ValueError(f"{path} 缺少 'epoch' 列")
        out[seed] = df
    return out


def plot_alpha_curve(
    retrained_dir: str,
    output_dir: str,
    dpi: int,
) -> str:
    """绘制三种子的 α 训练曲线。"""
    curves = _load_alpha_curves(retrained_dir)

    _setup_publication_style(lang="zh")
    # Okabe-Ito 色盲安全配色 + 不同 marker 做冗余编码。
    palette = [
        (0.0, 0.45, 0.70),
        (0.84, 0.37, 0.0),
        (0.0, 0.62, 0.45),
    ]
    markers = ["o", "s", "^"]

    fig, ax = plt.subplots(figsize=(3.5, 2.625), constrained_layout=True)
    for idx, seed in enumerate(SEEDS):
        df = curves[seed]
        ax.plot(
            df["epoch"],
            df["adaptive_graph_alpha"],
            label=f"Seed {seed}",
            color=palette[idx],
            marker=markers[idx],
            markersize=3,
            markevery=max(1, len(df) // 6),
            linewidth=1.0,
        )
    ax.set_xlabel("Epoch")
    ax.set_ylabel(r"Fixed-graph weight $\alpha = \sigma(fixed\_weight)$")
    ax.set_title("Adaptive vs. fixed graph weight during training")
    ax.legend(frameon=False, loc="upper right")
    ax.set_ylim(bottom=0.0, top=max(0.7, ax.get_ylim()[1]))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    basename = os.path.join(output_dir, "fig_alpha_curve")
    if export_figure is not None:
        export_figure(
            fig,
            basename=basename,
            formats=["png", "pdf"],
            dpi=dpi,
            size_inches=(3.5, 2.625),
            tight=True,
            pad_inches=0.02,
        )
    else:
        os.makedirs(output_dir, exist_ok=True)
        fig.savefig(f"{basename}.png", dpi=dpi, bbox_inches="tight", pad_inches=0.02)
        fig.savefig(f"{basename}.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return f"{basename}.png"


def _rank_edges(matrix: np.ndarray) -> Dict[Tuple[int, int], int]:
    """返回上三角（不含自环）边按权重降序的排名字典，1 为最强。"""
    i, j = np.triu_indices(matrix.shape[0], k=1)
    vals = matrix[i, j]
    order = np.argsort(-vals)
    return {(int(i[k]), int(j[k])): rank + 1 for rank, k in enumerate(order)}


def analyze_top_edges(
    night_run_dir: str,
    seed: int,
    node_ids: List[str],
    retrained_dir: str,
    analysis_dir: str,
) -> str:
    """分析自适应混合邻接的 top-10 边并写出 JSON。"""
    relations = load_fixed_relations(os.path.join(night_run_dir, "relation_matrices.npz"))
    state = load_model_state(night_run_dir, seed)
    fixed_adjs = [relations["load"], relations["event"], relations["pattern"]]
    _, mixed, heatmap_alpha = _build_adaptive_adjacency(
        source_embedding=state["source_embedding"].numpy(),
        target_embedding=state["target_embedding"].numpy(),
        fixed_weight=state["fixed_weight"].item(),
        fixed_adjs=fixed_adjs,
        top_k=5,
    )

    num_nodes = mixed.shape[0]
    # 提取上三角非自环边。
    ui, uj = np.triu_indices(num_nodes, k=1)
    mixed_vals = mixed[ui, uj]
    top10_order = np.argsort(-mixed_vals)[:10]

    # 预计算各固定关系的边排名。
    relation_names = ["load", "event", "pattern"]
    ranks_per_relation = {
        name: _rank_edges(relations[name]) for name in relation_names
    }

    top_edges: List[Dict[str, object]] = []
    novel_edges: List[Dict[str, object]] = []
    for rank, idx in enumerate(top10_order, start=1):
        i = int(ui[idx])
        j = int(uj[idx])
        mixed_w = float(mixed_vals[idx])
        relation_ranks = {
            name: int(ranks_per_relation[name].get((i, j), -1)) for name in relation_names
        }
        relation_weights = {
            name: float(relations[name][i, j]) for name in relation_names
        }
        edge_info: Dict[str, object] = {
            "rank_in_mixed": rank,
            "node_pair": [node_ids[i], node_ids[j]],
            "mixed_weight": round(mixed_w, 6),
            "rank_in_load": relation_ranks["load"],
            "rank_in_event": relation_ranks["event"],
            "rank_in_pattern": relation_ranks["pattern"],
            "weight_in_load": round(relation_weights["load"], 6),
            "weight_in_event": round(relation_weights["event"], 6),
            "weight_in_pattern": round(relation_weights["pattern"], 6),
        }
        top_edges.append(edge_info)
        # 若该边在所有固定关系中均未进入 top-10，则视为自适应图新增连接。
        if all(r > 10 for r in relation_ranks.values()):
            novel_edges.append(edge_info)

    # 读取三种子的最终 α（来自重训练日志）。
    alpha_curves = _load_alpha_curves(retrained_dir)
    final_alpha = {
        str(seed): round(float(alpha_curves[seed]["adaptive_graph_alpha"].iloc[-1]), 6)
        for seed in SEEDS
    }

    findings = {
        "seed_used_for_heatmap": seed,
        "heatmap_alpha": round(float(heatmap_alpha), 6),
        "final_alpha_per_seed": final_alpha,
        "top_10_mixed_edges": top_edges,
        "novel_edges_count": len(novel_edges),
        "novel_edges": novel_edges,
        "note": (
            "Mixed adjacency top-10 排除自环；固定关系排名同样基于上三角非自环边。"
            "novel edge 定义为未进入任一固定关系 top-10 的连接。"
        ),
    }

    os.makedirs(analysis_dir, exist_ok=True)
    out_path = os.path.join(analysis_dir, "adaptive_graph_findings.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    return out_path


def main() -> None:
    """主入口：解析参数、绘制两张图、写出分析 JSON。"""
    args = parse_args()

    # 校验必要输入存在，失败时直接抛出。
    node_ids = load_node_list(args.node_list)
    load_fixed_relations(os.path.join(args.night_run_dir, "relation_matrices.npz"))
    for seed in SEEDS:
        _require_file(os.path.join(args.retrained_dir, f"seed-{seed}", "training_log.csv"))
        _require_file(os.path.join(args.night_run_dir, f"seed-{seed}", "model.pt"))

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.analysis_dir, exist_ok=True)

    heatmap_path = plot_heatmaps(
        night_run_dir=args.night_run_dir,
        seed=args.seed,
        node_ids=node_ids,
        output_dir=args.output_dir,
        dpi=args.dpi,
    )
    alpha_path = plot_alpha_curve(
        retrained_dir=args.retrained_dir,
        output_dir=args.output_dir,
        dpi=args.dpi,
    )
    findings_path = analyze_top_edges(
        night_run_dir=args.night_run_dir,
        seed=args.seed,
        node_ids=node_ids,
        retrained_dir=args.retrained_dir,
        analysis_dir=args.analysis_dir,
    )

    print("生成文件：")
    print(f"  热力图：{heatmap_path}")
    print(f"  α 曲线：{alpha_path}")
    print(f"  分析 JSON：{findings_path}")


if __name__ == "__main__":
    main()
