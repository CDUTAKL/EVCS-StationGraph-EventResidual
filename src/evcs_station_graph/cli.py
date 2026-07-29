"""研究项目统一命令入口。

所有数据构建、模型训练和机制实验均从这里进入，避免不同实验脚本自行解释
配置、切分或评价口径。
"""

from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from evcs_station_graph.config import load_experiment_config, load_yaml
from evcs_station_graph.data import build_tensor_artifact, load_tensor_bundle
from evcs_station_graph.experiments import run_formal_pipeline, run_mechanism_suite
from evcs_station_graph.training import train_experiment


def build_parser() -> argparse.ArgumentParser:
    """创建命令行解析器。"""
    parser = argparse.ArgumentParser(
        prog="evcs-sg",
        description="站内充电单元交互图与事件残差修正统一实验入口",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-data", help="生成十五分钟节点张量与预测键基础")
    prepare.add_argument("--project", default="configs/project.yaml")
    prepare.add_argument("--output")
    prepare.add_argument("--metadata")
    prepare.add_argument(
        "--max-time-steps",
        type=int,
        help="仅限冒烟测试；正式构建不得设置",
    )

    run = subparsers.add_parser("run", help="运行 SG-EXP-002～005 单项实验")
    run.add_argument("--project", default="configs/project.yaml")
    run.add_argument("--experiment", required=True)
    run.add_argument("--output-root")
    run.add_argument("--base-checkpoint")
    run.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="覆盖配置项，可重复使用",
    )

    mechanism = subparsers.add_parser("run-mechanism", help="运行 SG-EXP-006 机制实验")
    mechanism.add_argument("--project", default="configs/project.yaml")
    mechanism.add_argument(
        "--suite",
        default="configs/experiments/SG-EXP-006-mechanism.yaml",
    )
    mechanism.add_argument("--output-root")
    mechanism.add_argument("--base-checkpoint", required=True)
    mechanism.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
    )

    pipeline = subparsers.add_parser(
        "run-pipeline",
        help="按正式顺序运行 SG-EXP-002～006",
    )
    pipeline.add_argument("--project", default="configs/project.yaml")
    pipeline.add_argument(
        "--suite",
        default="configs/experiments/SG-EXP-006-mechanism.yaml",
    )
    pipeline.add_argument("--output-root")
    pipeline.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="受控调试覆盖项；正式运行通常不使用",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """执行命令并打印最终工件目录。"""
    args = build_parser().parse_args(argv)
    project_path = Path(args.project).expanduser().resolve()
    project_root = _infer_project_root(project_path)
    with _working_directory(project_root):
        if args.command == "prepare-data":
            project_config = load_yaml(project_path)
            artifact, metadata = build_tensor_artifact(
                project_config,
                output_path=args.output,
                metadata_path=args.metadata,
                max_time_steps=args.max_time_steps,
            )
            print(f"节点张量：{artifact}")
            print(f"数据清单：{metadata}")
            return 0

        if args.command == "run":
            experiment_path = _resolve_from_project_root(args.experiment, project_root)
            config = load_experiment_config(
                project_path,
                experiment_path,
                tuple(args.overrides),
            )
            bundle = load_tensor_bundle(config["paths"]["dataset_artifact"])
            output_root = args.output_root or config["runtime"]["output_root"]
            run_root = train_experiment(
                config,
                bundle,
                output_root,
                base_checkpoint=args.base_checkpoint,
            )
            print(f"实验工件：{run_root}")
            return 0

        suite_path = _resolve_from_project_root(args.suite, project_root)
        orchestration_config = _load_orchestration_config(
            project_path,
            suite_path,
            tuple(args.overrides),
            command=args.command,
        )
        bundle = load_tensor_bundle(orchestration_config["paths"]["dataset_artifact"])
        output_root = args.output_root or orchestration_config["runtime"]["output_root"]
        if args.command == "run-pipeline":
            run_root = run_formal_pipeline(
                project_path,
                bundle,
                output_root,
                mechanism_suite_path=suite_path,
                overrides=tuple(args.overrides),
            )
            print(f"正式流水线工件：{run_root}")
            return 0
        run_root = run_mechanism_suite(
            project_path,
            suite_path,
            bundle,
            output_root,
            base_checkpoint=args.base_checkpoint,
            overrides=tuple(args.overrides),
        )
        print(f"机制实验工件：{run_root}")
        return 0


def _infer_project_root(project_path: Path) -> Path:
    """由项目配置位置推断仓库根目录。"""
    if project_path.parent.name == "configs":
        return project_path.parent.parent
    return project_path.parent


def _resolve_from_project_root(raw_path: str, project_root: Path) -> Path:
    """让子配置路径始终相对于仓库根目录，而非调用者当前目录。"""
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (project_root / candidate).resolve()


def _load_orchestration_config(
    project_path: Path,
    suite_path: Path,
    overrides: tuple[str, ...],
    *,
    command: str,
) -> dict:
    """读取编排命令实际使用的数据与运行路径。

    机制实验以套件声明的基础实验为准；完整流水线以首个正式实验为准。
    两者都必须先应用命令行覆盖项，再读取节点张量。否则冒烟测试可能错误地
    读取正式数据路径，也会造成“配置已覆盖、数据却未覆盖”的口径分裂。
    """
    if command == "run-mechanism":
        suite = load_yaml(suite_path)
        experiment_path = suite["base_experiment_config"]
    else:
        experiment_path = "configs/experiments/SG-EXP-002-temporal-baseline.yaml"
    return load_experiment_config(project_path, experiment_path, overrides)


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    """让配置中的相对路径稳定地相对于项目根目录解释。"""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


if __name__ == "__main__":
    raise SystemExit(main())
