"""随机性控制、文件校验与运行环境快照。"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch


def set_global_seed(seed: int, deterministic: bool = True) -> None:
    """设置 Python、NumPy 与 PyTorch 随机种子，确保实验可复现。

    确定性模式（deterministic=True）：
    - 启用 PyTorch 确定性算法，牺牲少量性能换取 bitwise 可复现
    - ``CUBLAS_WORKSPACE_CONFIG=:4096:8`` 是 cuBLAS 确定性模式必需的
      环境变量：4096 表示最大工作空间（字节），8 表示启用确定性模式
    - ``warn_only=True``：遇到无法确定化的算子时仅警告而非崩溃，
      因为当前实验不依赖那些算子的 bitwise 复现
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """计算文件 SHA-256 校验和，用于数据工件完整性验证。

    采用分块读取（默认 1 MB）避免大文件一次性加载到内存。
    校验和记录在数据清单中，确保下游实验使用的是未经篡改的数据。
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def environment_snapshot() -> dict[str, Any]:
    """收集不含凭据的最小运行环境信息。"""
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "device_count": torch.cuda.device_count(),
        "git_commit": _git_commit(),
    }


def write_json(value: Any, path: str | Path) -> None:
    """以稳定格式写入 JSON。"""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
