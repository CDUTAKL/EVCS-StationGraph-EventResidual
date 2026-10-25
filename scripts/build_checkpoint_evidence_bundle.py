#!/usr/bin/env python3
"""Assemble local inference evidence; never train or modify historical runs."""
import argparse, hashlib, json, shutil, tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
JPL = ROOT.parent / '2026-10-05/sg-exp-028-jpl/outputs/recovered/SG-EXP-028/extracted'
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def copy_tree(src, dst):
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
            if p.is_symlink(): raise ValueError(f'Symlink refused: {p}')
            q = dst / p.relative_to(src); q.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p,q)
def extract_upload(src,dst):
    with tarfile.open(src) as t:
        for m in t.getmembers():
            parts=PurePosixPath(m.name).parts
            if not parts or parts[0]!='evcs-eventtime' or '..' in parts or m.issym() or m.islnk():
                raise ValueError(f'Unsafe archive member: {m.name}')
            if not m.isfile(): continue
            q=dst.joinpath(*parts[1:]); q.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(m) as f, q.open('wb') as o: shutil.copyfileobj(f,o)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True); args=ap.parse_args()
    out=args.out.resolve()
    if out.exists(): raise ValueError('Output must be a new directory')
    out.mkdir(parents=True)
    provenance=[]
    for key, upload, results in [
      ('sg019', ROOT/'outputs/releases/SG-EXP-019/evcs-eventtime-autodl-4gpu-v3.tar.gz', ROOT/'outputs/recovered/SG-EXP-019/unpacked/results/formal'),
      ('sg027', ROOT/'outputs/experiments/SG-EXP-027/upload/gate-control-20261004.tar.gz', ROOT/'outputs/experiments/SG-EXP-027/recovered/formal')]:
        dst=out/'components'/key; extract_upload(upload,dst); copy_tree(results,dst/'results/formal')
        provenance.append({'component':key,'source_upload':str(upload.relative_to(ROOT)),'upload_sha256':sha(upload),'source_status':'original frozen upload with source digest linked to saved configs'})
    dst=out/'components/sg028'; dst.mkdir(parents=True)
    original=json.loads((JPL/'BUNDLE_MANIFEST.json').read_text())
    for rel,digest in original.items():
        p=JPL/rel
        if not p.is_relative_to(JPL) or sha(p)!=digest: raise ValueError(f'JPL source mismatch: {rel}')
        q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    shutil.copy2(JPL/'BUNDLE_MANIFEST.json',dst/'BUNDLE_MANIFEST.json')
    copy_tree(JPL/'results',dst/'results')
    provenance.append({'component':'sg028','source_bundle':'SG-EXP-028 recovered standalone bundle','bundle_manifest_sha256':sha(JPL/'BUNDLE_MANIFEST.json'),'source_status':'original frozen bundle and pre-test checkpoint lock'})
    dst=out/'components/legacy';copy_tree(ROOT/'src',dst/'src')
    (dst/'data').mkdir(parents=True)
    shutil.copy2(ROOT/'data/processed/SG-DATA-005-primary-tensor.npz',dst/'data/dataset.npz')
    for exp in ['SG-EXP-003','SG-EXP-002','SG-EXP-004']:
        copy_tree(ROOT/'outputs/night_run/20260730-171821'/exp/'20260730-171821',dst/'results'/exp)
    provenance.append({'component':'legacy','source_status':'reconstruction runtime snapshot; training-time source authenticity NOT established','historical_source_gap':True,'tensor_sha256':sha(dst/'data/dataset.npz')})
    for name in ['replay_checkpoint_evidence.py','replay_sgexp028_checkpoints.py']:
        shutil.copy2(ROOT/'scripts'/name,out/name)
    (out/'requirements-replay.txt').write_text('numpy==2.3.5\ntorch==2.13.0\npandas==2.2.3\nPyYAML==6.0.3\n',encoding='utf-8')
    (out/'README.md').write_text('''# 跨协议检查点推理证据包

仅供获授权的本地研究交接；未确认派生数据、完整预测及权重的公开再分发许可。无原始会话、访问凭据或训练入口调用。

## 范围与运行

冻结输入：旧回溯协议3模型×3种子；SG-EXP-019正式12模型×3种子；SG-EXP-027两门控×3种子；SG-EXP-028四模型×3种子，共63次测试集推理。保留原tuning/calibration预测用于追溯，本入口只复算test，不声称已前向复算所有切分。

在已有Python环境中安装requirements-replay.txt；保留各组件原训练环境记录。联网安装依赖由接收方自行完成。本轮核验在现有环境执行，未验证全新环境安装。

```sh
python replay_checkpoint_evidence.py --verify-only
python replay_checkpoint_evidence.py --out replay-results
```

全部路径相对本脚本所在目录；可从其他工作目录调用。四个组件各用独立子进程，避免不同版本源码互相覆盖。逐文件SHA256校验先于推理；结果写至指定新目录，不回写冻结组件。PASS要求63个运行及键、标签、时间戳、来源摘要和数值容差全部通过。误差容差在脚本中预先给定，失败不会自动放宽。

旧协议源码只是当前复算快照，训练时源码与完整GPU环境未认证；保存原配置，运行时按检查点权重形状恢复网络层数并显式记录，不修改历史配置。旧协议含回溯代理信息，不能合并为严格事件时刻输入。PCMCI历史名义检验完整p矩阵及训练时版本仍缺，本包不补造。CPU前向成功不等于从随机初始化复现训练，不证明历史选模从未查看测试期。

MANIFEST.json覆盖所有冻结输入与运行脚本，PROVENANCE.json记录原上传包及证据状态。接收后先核对外部记录的MANIFEST与压缩包SHA256；包内自校验不能独立认证来源。
''',encoding='utf-8')
    (out/'PROVENANCE.json').write_text(json.dumps({'scope_runs':63,'retraining_performed':False,'components':provenance},indent=2,ensure_ascii=False)+'\n')
    manifest={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'directory':str(out),'files':len(manifest),'manifest_sha256':sha(out/'MANIFEST.json'),'bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file())},ensure_ascii=False))
if __name__=='__main__':main()
