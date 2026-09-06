"""Task planning for one independent CUDA process per visible GPU."""
from dataclasses import dataclass

from .models import MODELS, PHASE1, PHASE2


@dataclass(frozen=True)
class ExperimentTask:
    model: str
    seed: int
    index: int


def parse_gpu_ids(value: str) -> tuple[int, ...]:
    try:
        ids = tuple(int(item.strip()) for item in value.split(',') if item.strip())
    except ValueError as exc:
        raise ValueError('GPU list must be comma-separated non-negative integers') from exc
    if len(ids) != 4 or len(set(ids)) != 4 or any(i < 0 for i in ids):
        raise ValueError('Exactly four distinct non-negative GPU ids are required')
    return ids


def build_tasks(stage: str, model: str | None = None) -> tuple[ExperimentTask, ...]:
    if stage == 'phase1':
        names, seeds = PHASE1, (2024, 2025, 2026)
    elif stage == 'phase2':
        names, seeds = PHASE2, (2024, 2025, 2026)
    elif stage == 'all':
        names, seeds = MODELS, (2024, 2025, 2026)
    elif stage == 'smoke':
        names, seeds = MODELS, (2024,)
    elif stage == 'benchmark':
        names, seeds = (model or 'mrg_full',), (2024,)
    else:
        raise ValueError(f'Unknown parallel stage: {stage}')
    return tuple(ExperimentTask(name, seed, i) for i, (name, seed) in enumerate(
        (pair for name in names for pair in ((name, seed) for seed in seeds))))


def assign_gpu(task_index: int, gpu_ids: tuple[int, ...]) -> int:
    if not gpu_ids:
        raise ValueError('At least one GPU is required')
    return gpu_ids[task_index % len(gpu_ids)]


def namespace(stage: str) -> str:
    return 'smoke' if stage == 'smoke' else 'benchmark' if stage == 'benchmark' else 'formal'


def output_dir(task: ExperimentTask, root=None, stage: str = 'all'):
    base = 'results' if root is None else root
    from pathlib import Path
    return Path(base) / namespace(stage) / task.model / f'seed-{task.seed}'
