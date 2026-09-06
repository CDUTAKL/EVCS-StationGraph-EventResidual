#!/usr/bin/env python3
"""Save cloud exit evidence and a checksum archive; NEVER shuts down a machine."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--log-dir', type=Path, required=True)
    p.add_argument('--exit-code', type=int, required=True)
    p.add_argument('--auto-shutdown', choices=['0','1'], required=True)
    args = p.parse_args()
    root, log = args.root.resolve(), args.log_dir.resolve()
    log.relative_to(root/'results')
    archive_dir = root/'archives'
    archive_dir.mkdir(exist_ok=True)
    archive = archive_dir/(log.name+'.tar.gz')
    if archive.exists():
        raise FileExistsError(f'Archive exists: {archive}')
    (log/'exit_code.txt').write_text(str(args.exit_code)+'\n')
    summary = dict(exit_code=args.exit_code, archive_path=str(archive),
                   shutdown_status='scheduled_by_wrapper_not_confirmed' if args.auto_shutdown=='1' else 'disabled',
                   archive_status='preparing', results_path=str(root/'results'))
    (log/'autodl_run_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    files = sorted(p for p in (root/'results').rglob('*') if p.is_file() and not p.is_symlink())
    with tarfile.open(archive, 'w:gz', compresslevel=1) as tar:
        for file in files:
            tar.add(file, arcname=str(file.relative_to(root)), recursive=False)
    with archive.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    checksums = f'{digest}  {archive.name}\n'
    archive.with_suffix('.sha256').write_text(checksums)
    (log/'checksums.sha256').write_text(checksums)
    summary.update(archive_status='created', archive_sha256=digest)
    # Final index is beside archive; archive contains its pre-archive record.
    (log/'autodl_run_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    archive.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
