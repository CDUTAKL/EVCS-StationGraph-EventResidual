#!/usr/bin/env python3
"""Run independent event-time experiments concurrently, one process per GPU."""
from __future__ import annotations

import argparse
from collections import deque
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))

from evcs_station_graph.eventtime.parallel import (  # noqa: E402
    assign_gpu, build_tasks, output_dir, parse_gpu_ids,
)


def plan(stage, gpu_ids, root, out, resume, model=None):
    tasks = build_tasks(stage, model=model)
    entries = []
    for task in tasks:
        gpu = assign_gpu(task.index, gpu_ids)
        folder = output_dir(task, out, stage)
        entries.append(dict(index=task.index, model=task.model, seed=task.seed,
                            gpu=gpu, CUDA_VISIBLE_DEVICES=str(gpu), output=str(folder),
                            resume_checkpoint_present=bool(resume and (folder/'last.pt').exists())))
    return tasks, entries


def command(task, root, out, stage, resume):
    args = [sys.executable, str(root/'scripts/eventtime_experiment.py'), 'train',
            '--model', task.model, '--seed', str(task.seed), '--device', 'cuda', '--out', str(out),
            '--run-stage', 'smoke' if stage == 'smoke' else 'benchmark' if stage == 'benchmark' else 'formal']
    if resume:
        args.append('--resume')
    return args


def run(stage, gpu_ids, root, out, resume, model=None):
    tasks, _ = plan(stage, gpu_ids, root, out, resume, model=model)
    pending = deque(tasks)
    logs = out/'parallel_logs'
    logs.mkdir(parents=True, exist_ok=True)
    active = {}
    stop_requested = False

    def stop_children(_signum, _frame):
        nonlocal stop_requested
        stop_requested = True
        for process, _, _ in active.values():
            process.terminate()

    old_int = signal.signal(signal.SIGINT, stop_children)
    old_term = signal.signal(signal.SIGTERM, stop_children)

    def launch(gpu, task):
        folder = output_dir(task, out, stage)
        can_resume = resume and (folder/'last.pt').exists()
        log_path = logs/f'{task.index:02d}-{task.model}-seed-{task.seed}-gpu-{gpu}.log'
        log = log_path.open('a', encoding='utf-8')
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = str(gpu)
        env.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
        process = subprocess.Popen(command(task, root, out, stage, can_resume), cwd=root, env=env,
                                   stdout=log, stderr=subprocess.STDOUT, text=True)
        active[gpu] = (process, log, task)
        print(json.dumps(dict(event='started', model=task.model, seed=task.seed,
                              gpu=gpu, pid=process.pid, log=str(log_path))), flush=True)

    try:
        for gpu in gpu_ids:
            if pending:
                launch(gpu, pending.popleft())
        completed = 0
        while active:
            if stop_requested:
                raise KeyboardInterrupt
            progressed = False
            for gpu, (process, log, task) in list(active.items()):
                return_code = process.poll()
                if return_code is None:
                    continue
                progressed = True
                log.close()
                del active[gpu]
                if return_code != 0:
                    for child, child_log, _ in active.values():
                        child.terminate()
                        child_log.close()
                    raise RuntimeError(f'Experiment failed: {task.model}/seed-{task.seed} '
                                       f'on GPU {gpu}, exit={return_code}')
                completed += 1
                print(json.dumps(dict(event='completed', model=task.model, seed=task.seed,
                                      gpu=gpu, completed=completed, total=len(tasks))), flush=True)
                if pending:
                    launch(gpu, pending.popleft())
            if not progressed:
                time.sleep(.5)
    except BaseException:
        for child, child_log, _ in active.values():
            child.terminate()
            child_log.close()
        raise
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
    print(json.dumps(dict(event='all_completed', stage=stage, task_count=len(tasks),
                          worker_count=len(gpu_ids))), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['smoke', 'benchmark', 'phase1', 'phase2', 'all'])
    parser.add_argument('--gpus', default='0,1,2,3', help='exactly four physical GPU ids')
    parser.add_argument('--out', type=Path, default=ROOT/'results')
    parser.add_argument('--model', choices=['mrg_full', 'agcrn_full'], default=None,
                        help='benchmark model; only used with benchmark')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    gpu_ids = parse_gpu_ids(args.gpus)
    if args.model is not None and args.stage != 'benchmark':
        parser.error('--model is only valid with benchmark')
    tasks, entries = plan(args.stage, gpu_ids, ROOT, args.out, args.resume, model=args.model)
    if args.dry_run:
        counts = {str(gpu): sum(entry['gpu'] == gpu for entry in entries) for gpu in gpu_ids}
        print(json.dumps(dict(stage=args.stage, task_count=len(tasks), worker_count=len(gpu_ids),
                              assignment_counts=counts, tasks=[dict(entry, command=command(
                                  task, ROOT, args.out, args.stage, args.resume)) for task, entry in zip(tasks, entries)]), indent=2))
        return
    run(args.stage, gpu_ids, ROOT, args.out, args.resume, model=args.model)


if __name__ == '__main__':
    main()
