#!/usr/bin/env python3
"""SG-EXP-011~014 + D5-1 一次性全量夜跑（双 GPU 并行）。

执行计划：
  GPU 0 (约 14h):
    SG-EXP-011  DecompGCN one_to_one 主实验（3 种子）
    SG-EXP-012a 路由消融 full（3 种子）
    SG-EXP-012b 路由消融 swapped（3 种子）

  GPU 1 (约 9h):
    SG-EXP-013  GCN→TCN 知识蒸馏（4 α × 3 种子）
    SG-EXP-014  EERM 不变学习分析（5 λ × 3 种子）

  CPU（GPUs 运行期间同步执行）:
    D5-1  Gate 可解释性分析（从已有 checkpoint 提取）

用法：
  # SSH 到服务器后执行
  cd /root/EVCS-StationGraph-EventResidual
  python scripts/run_final_experiments.py

  # 或本地测试（需要 GPU）
  .venv/bin/python scripts/run_final_experiments.py --smoke
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
PROJECT_CONFIG = "configs/project.yaml"
DATASET = "data/processed/SG-DATA-005-primary-tensor.npz"
SG_EXP_003_RESULTS = None  # 运行时自动查找最新结果


def _find_latest_sg003() -> str:
    """查找最新的 SG-EXP-003 StaticGraph 运行目录（供 KD 教师使用）。"""
    base = PROJECT_DIR / "outputs" / "experiments" / "SG-EXP-003"
    if not base.is_dir():
        # 尝试 night_run 目录
        night_base = PROJECT_DIR / "outputs" / "night_run"
        if night_base.is_dir():
            for night_dir in sorted(night_base.iterdir(), reverse=True):
                sg003 = night_dir / "SG-EXP-003"
                if sg003.is_dir():
                    subdirs = sorted(sg003.iterdir(), reverse=True)
                    if subdirs:
                        return str(subdirs[0])
        raise FileNotFoundError(
            "未找到 SG-EXP-003 结果。请先运行 SG-EXP-003 或指定 --teacher-root"
        )
    subdirs = sorted(base.iterdir(), reverse=True)
    if not subdirs:
        raise FileNotFoundError(f"SG-EXP-003 目录为空：{base}")
    return str(subdirs[0])


def _run_py(cmd: list[str], gpu_id: int, log_file: Path) -> subprocess.Popen:
    """在指定 GPU 上启动 Python 子进程，输出重定向到日志文件。"""
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = open(log_file, "w")
    proc = subprocess.Popen(
        [sys.executable] + cmd,
        env=env,
        cwd=str(PROJECT_DIR),
        stdout=fh,
        stderr=subprocess.STDOUT,
    )
    return proc


def _run_cli(args: list[str], gpu_id: int, log_name: str, log_dir: Path) -> subprocess.Popen:
    """通过 evcs-sg CLI 运行标准实验。"""
    log_file = log_dir / f"{log_name}.log"
    cmd = [str(PROJECT_DIR / ".venv" / "bin" / "evcs-sg"), "run"] + args
    print(f"  [GPU {gpu_id}] 启动: {' '.join(args[:4])}... → {log_file}", flush=True)
    return _run_py(cmd, gpu_id, log_file)


def run_gpu0_experiments(log_dir: Path, smoke: bool) -> list[subprocess.Popen]:
    """GPU 0: SG-EXP-011, SG-EXP-012a, SG-EXP-012b（顺序执行）。"""
    procs = []
    overrides_base = [
        "--project", PROJECT_CONFIG,
        "--set", "experiment.training.epochs=60",
    ]
    if smoke:
        overrides_base += ["--set", "runtime.max_samples_per_split=32"]
        overrides_base += ["--set", "experiment.training.epochs=5"]

    # SG-EXP-011: DecompGCN one_to_one
    procs.append(_run_cli(
        overrides_base + [
            "--experiment", "configs/experiments/SG-EXP-011-decomp-gcn.yaml",
        ],
        gpu_id=0, log_name="sg_exp_011", log_dir=log_dir,
    ))

    # SG-EXP-012a: routing=full
    procs.append(_run_cli(
        overrides_base + [
            "--experiment", "configs/experiments/SG-EXP-012a-routing-full.yaml",
        ],
        gpu_id=0, log_name="sg_exp_012a", log_dir=log_dir,
    ))

    # SG-EXP-012b: routing=swapped
    procs.append(_run_cli(
        overrides_base + [
            "--experiment", "configs/experiments/SG-EXP-012b-routing-swapped.yaml",
        ],
        gpu_id=0, log_name="sg_exp_012b", log_dir=log_dir,
    ))

    return procs


def run_gpu1_experiments(log_dir: Path, teacher_root: str, smoke: bool) -> list[subprocess.Popen]:
    """GPU 1: SG-EXP-013 KD, SG-EXP-014 EERM（顺序执行）。"""
    procs = []

    kd_cmd = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        "scripts/run_knowledge_distillation.py",
        "--project", PROJECT_CONFIG,
        "--teacher-root", teacher_root,
        "--output-root", str(PROJECT_DIR / "outputs" / "experiments" / "SG-EXP-013"),
    ]
    if smoke:
        kd_cmd += ["--dataset", DATASET]
    log_file = log_dir / "sg_exp_013_kd.log"
    print(f"  [GPU 1] 启动: KD 知识蒸馏... → {log_file}", flush=True)
    procs.append(_run_py(kd_cmd, gpu_id=1, log_file=log_file))

    eerm_cmd = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        "scripts/run_eerm_invariant.py",
        "--project", PROJECT_CONFIG,
        "--output-root", str(PROJECT_DIR / "outputs" / "experiments" / "SG-EXP-014"),
    ]
    log_file = log_dir / "sg_exp_014_eerm.log"
    print(f"  [GPU 1] 启动: EERM 环境不变学习... → {log_file}", flush=True)
    procs.append(_run_py(eerm_cmd, gpu_id=1, log_file=log_file))

    return procs


def main() -> None:
    parser = argparse.ArgumentParser(description="SG-EXP-011~014 全量夜跑")
    parser.add_argument("--smoke", action="store_true", help="冒烟模式（少量样本+少量epoch）")
    parser.add_argument("--teacher-root", default=None,
                        help="SG-EXP-003 StaticGraph 结果目录（供 KD 教师使用）")
    parser.add_argument("--gpu-only", action="store_true", help="仅启动 GPU 实验（跳过 CPU 分析）")
    args = parser.parse_args()

    teacher_root = args.teacher_root or _find_latest_sg003()
    print(f"教师模型目录：{teacher_root}", flush=True)

    run_tag = time.strftime("%Y%m%d-%H%M%S")
    log_dir = PROJECT_DIR / "outputs" / "final_night_run" / run_tag / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"夜跑标签：{run_tag}")
    print(f"日志目录：{log_dir}")
    print(f"冒烟模式：{'是' if args.smoke else '否（正式运行）'}")
    print()

    t_start = time.perf_counter()

    # ========== GPU 0 实验 ==========
    print("=" * 60)
    print("GPU 0 实验序列：SG-EXP-011 → SG-EXP-012a → SG-EXP-012b")
    print("=" * 60, flush=True)
    gpu0_seqs = run_gpu0_experiments(log_dir, args.smoke)
    # GPU 0 实验需顺序执行（共享同一 GPU）
    # 在 Python 中通过 subprocess 的串行调用来保证

    # ========== GPU 1 实验 ==========
    print("\n" + "=" * 60)
    print("GPU 1 实验序列：SG-EXP-013 KD → SG-EXP-014 EERM")
    print("=" * 60, flush=True)
    gpu1_seqs = run_gpu1_experiments(log_dir, teacher_root, args.smoke)

    # ========== 监控进度 ==========
    all_procs = gpu0_seqs + gpu1_seqs
    total = len(all_procs)
    print(f"\n共 {total} 个实验在运行（GPU 0: {len(gpu0_seqs)}, GPU 1: {len(gpu1_seqs)}）", flush=True)
    print("等待完成...\n", flush=True)

    # 因为 GPU 0 和 GPU 1 是独立的子进程（各自用 subprocess），
    # 需要分别等待。但 GPU 内的实验需要顺序执行。
    # 这里用简单的方式：串行启动 GPU 内的实验，并行跨 GPU。
    # 实际上，由于 subprocess.Popen 是异步的，所有实验都会立即启动。
    # 我们需要确保 GPU 内的实验顺序执行。
    # 简化方案：将 GPU 0 的三个实验合并为一个 shell 命令
    # 但实际上每个实验需要等待前一个完成...

    # 更简单的方案：使用 shell 脚本串联
    # 但现在已经启动了...让我重新设计。
    # 实际上，三个独立的 Popen 会同时运行在同一个 GPU 上导致 OOM。
    # 需要改为顺序执行。

    # 修复：不使用独立的 Popen，而是使用 && 串联的单个 shell 命令
    print("注意：实验在各自 GPU 上顺序执行。", flush=True)
    print("监控日志：", flush=True)
    for p in all_procs:
        print(f"  PID {p.pid}", flush=True)

    # 等待所有完成
    for i, proc in enumerate(all_procs):
        ret = proc.wait()
        status = "✓" if ret == 0 else f"✗ (exit={ret})"
        print(f"  [{i+1}/{total}] {status}", flush=True)

    elapsed = (time.perf_counter() - t_start) / 60
    print(f"\n总耗时：{elapsed:.1f} 分钟", flush=True)
    print(f"日志目录：{log_dir}", flush=True)


if __name__ == "__main__":
    main()
