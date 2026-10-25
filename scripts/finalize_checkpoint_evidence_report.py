#!/usr/bin/env python3
"""Record actual cross-protocol audit outcomes and synchronize manuscript wording."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/thesis/reproducibility-20261012'
RESULTS=ROOT/'outputs/evidence/checkpoint-replay-results-20261012'
def sci(x):
 mantissa, exponent = f'{x:.3g}'.split('e')
 power = str(int(exponent)).translate(str.maketrans('-0123456789','⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))
 return mantissa+'×10'+power
def main():
 s=json.loads((RESULTS/'summary.json').read_text());allrows=[];table=[]
 labels={'legacy':'Caltech回溯（3模型）','sg019':'Caltech事件时刻 SG-EXP-019','sg027':'同参数门控 SG-EXP-027','sg028':'JPL重拟合 SG-EXP-028'}
 for c,v in s['protocols'].items():
  rows=v.get('runs',[]);allrows+=rows;passed=sum(r['status']=='PASS' for r in rows)
  table.append(f"| {labels[c]} | {len(rows)} | {passed} | {len(rows)-passed} | {max(r['max_prediction_abs_diff'] for r in rows):.4g} | {max(r['mae_abs_diff'] for r in rows):.4g} |")
 if len(allrows)!=63:raise ValueError('Incomplete replay; retain draft and repair missing components')
 passed=sum(r['status']=='PASS' for r in allrows)
 for p in RESULTS.glob('*.json'):shutil.copy2(p,OUT/('checkpoint-summary.json' if p.name=='summary.json' else p.name))
 text='''# 跨协议测试集检查点前向核验

输入包MANIFEST SHA256：`MANIFEST_HASH`。各组件源码分别在独立进程载入。输出目录与冻结组件分离。

| 协议/实验 | 运行数 | PASS | FAIL | 最大逐键预测差 | 最大全局MAE差 |
|---|---:|---:|---:|---:|---:|
TABLE

实际共TOTAL次运行，PASSED次通过、FAILED次未通过；总入口保留原始FAIL状态，不因大部分通过而改为全包PASS。原预测到指标独立复核63/63通过；论文21行MAE均值/样本标准差均与原预测指标相符。数值单位均为kWh/15 min。

通过的前向运行要求完整测试键、真值、标签、规则及时间戳核验，并检查六类指标：MAE、RMSE、事件/稳定MAE、逐目标片MAE、逐节点MAE。SG-EXP-019/027另核对四格计数及加权MAE闭合。JPL核对测试导出前的检查点锁和测试导出状态。预测/指标预设容差均为5×10⁻⁶，未更改阈值。

旧AdaptiveGraph三次未通过；其原预测和原指标的算术链仍一致，但当前CPU前向不能复现归档GPU输出。权重存在top-k边界并列，可能导致不同后端选边，尚未用原CUDA环境确认。不得以归档算术通过替代前向通过，也不得从原预测倒推选边强行匹配。

旧模型源码为当前复算快照，原训练环境git_commit为空；仍缺训练时版本认证。历史PCMCI+完整p矩阵及版本缺口同样保留。本轮没有重新训练、改写原权重、改写原预测、重做选模或放宽任何容差。

测试范围不包括tuning/calibration前向、表3-4的其他基线、全部区间/置换检验、数据重建及全新机器依赖安装。可携带性是在仓库外临时目录、现有Python环境中实际执行，不能扩大为所有环境复现已通过。
'''
 text=text.replace('MANIFEST_HASH',s['manifest_sha256']).replace('TABLE','\n'.join(table)).replace('TOTAL',str(len(allrows))).replace('PASSED',str(passed)).replace('FAILED',str(len(allrows)-passed))
 (OUT/'checkpoint-replay-report.md').write_text(text)
 p=ROOT/'docs/thesis/thesis-manuscript.md';source=p.read_text()
 marker='### 3.6.2 Caltech事件时刻协议的预测结果'
 paragraph=f'为复核主要表格的数值来源，本文从冻结张量和现有检查点对三套协议、四组实验执行测试集前向检查，共63次运行，{passed}次通过预设的5×10⁻⁶逐键预测与指标容差。另从63份原测试预测独立重算全局、分层、逐目标片和逐节点指标，全部通过，最大指标差为3.19×10⁻¹⁰。复核材料按协议封装源码、配置、检查点、原预测和哈希清单，并在原仓库之外运行。该检查验证现有权重到预测和指标的对应关系；旧协议训练时源码尚未认证，不将推理复算等同于从头训练复现。未通过项与逐运行记录保留于项目复核附件。'
 if '为复核主要表格的数值来源' not in source:source=source.replace(marker,paragraph+'\n\n'+marker)
 old='为核验表3-3由检查点到论文数字的复算链，本研究从锁定的12个best检查点在CPU上逐键重放JPL测试集，并核对时间键、标签、规则掩码及全局、分层、逐目标片和逐节点指标。每个运行均复核632,640个预测键；12/12通过，重放与归档GPU预测的最大绝对差为2.7×10⁻⁶，重算MAE与归档MAE的最大差为4.11×10⁻⁹，均不超过5×10⁻⁶容差。该检查确认表3-3指标可由冻结数据和归档检查点复算；它不重建训练过程，也不等同于重新训练复现。逐运行结果、数据哈希和复算脚本登记于项目复核附件。'
 jpl=s['protocols']['sg028']['runs'];jpass=sum(r['status']=='PASS' for r in jpl)
 new=f'JPL的{jpass}/12个锁定检查点通过上述逐键复核，每运行覆盖632,640个测试键；CPU重放与归档GPU预测的最大绝对差为{sci(max(r["max_prediction_abs_diff"] for r in jpl))}，全局MAE最大差为{sci(max(r["mae_abs_diff"] for r in jpl))}，均低于预设容差。表3-3的复算链及检查点锁登记于项目复核附件。'
 if jpass!=12:raise ValueError('Do not state JPL tolerance success if any run failed')
 if old not in source:raise ValueError('Original JPL paragraph not found')
 source=source.replace(old,new)
 note='注：MAE与RMSE单位为kWh/15 min，WAPE无量纲。随机初始化模型为三种子均值，标准差为$n=3$样本标准差，计算时分母为$n-1$，对应自由度为2；确定性基线标“—”。ARIMA正式结果未提供WAPE。各列加粗值为该指标的最小值。'
 extra='本轮CPU前向复核中，TCN与MRG-GCN各三个种子通过；AdaptiveGraph三个种子未通过逐键容差核验，其表值仍由原GPU预测导出及指标重算支撑，不计为已完成跨后端复现的结果。'
 if note not in source:raise ValueError('Legacy table note not found')
 source=source.replace(note,note+'\n\n'+extra)
 p.write_text(source)
 h=hashlib.sha256(p.read_bytes()).hexdigest();shutil.copy2(p,OUT/'manuscript-frozen.md')
 a=json.loads((OUT/'local-repair-audit.json').read_text());a['final_manuscript_sha256']=h
 (OUT/'local-repair-audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
 p=OUT/'README.md';text=p.read_text();text=text.replace('完整推理结束后以`checkpoint-summary.json`及逐组件记录为准；失败项必须保留，不能把范围清点数当成成功数。',f'前向复算已完成：**{passed}/63通过、{63-passed}次未通过**。总入口保留FAIL状态；具体结果见`checkpoint-replay-report.md`、`checkpoint-summary.json`及逐组件记录，不能把范围清点数当成成功数。')
 p.write_text(text)
 for path,section in [
 ('docs/thesis/data-availability.md',f'''\n## 2026-10-12 跨协议检查点证据包\n\n新增`MAT-CHECKPOINT-REPLAY-20261012`，复用SG-DATA-005/006/007及原实验权重，不新增原始数据。三个协议、四组实验共63次完整test前向，{passed}次通过、{63-passed}次未通过；原预测到六类指标复算63/63通过。来源、字段、权限与逐运行差异见`reproducibility-20261012/README.md`及`data-dictionary.md`。\n\n可携带输入目录为`outputs/evidence/checkpoint-replay-20261012`，MANIFEST覆盖1,022个冻结文件，SHA256为`{s['manifest_sha256']}`。实际从仓库外临时目录调用，在现有CPU环境执行；原tuning/calibration导出保留，本轮不声称完成其前向复算。旧AdaptiveGraph三个种子、训练时源码认证和历史PCMCI完整检验矩阵仍有缺口。原始会话、凭据未进入包；派生张量/权重/完整预测仅供授权本地教育研究交接，不进Git、不上传，公开再分发许可未确认。\n'''),
 ('docs/thesis/material-passport.md',f'''\n## 2026-10-12 新增复算与交接材料\n\n| 材料ID | 来源/完整性 | 核验结论 | 权限与范围 |\n|---|---|---|---|\n| MAT-CHECKPOINT-REPLAY-20261012 | 三个协议、四组实验原权重/配置/冻结张量；1,022文件MANIFEST SHA256 `{s['manifest_sha256']}` | {passed}/63 test前向通过；63/63原预测指标复算通过；21行论文MAE均值/样本SD一致 | 本地授权研究；不公开权重、预测或张量；不等同训练复现 |\n| MAT-ADAPTIVE-REPLAY-GAP-20261012 | 旧SG-EXP-004三种子及`adaptive-topk-diagnostic.json` | CPU前向失败如实保留；top-k并列值是候选解释，未作CUDA确认 | 不修改原结果；不能计为前向通过；训练时源码认证仍缺 |\n\n交接索引为`reproducibility-20261012/README.md`；原预测、模型与历史评分文件保持原证据身份，未用当前PCMCI结果填补历史完整p矩阵。\n''')]:
  p=ROOT/path
  if '2026-10-12 跨协议检查点证据包' in p.read_text() or '2026-10-12 新增复算与交接材料' in p.read_text():raise ValueError('Already finalized')
  with p.open('a') as f:f.write(section)
 print(json.dumps({'replay_passed':passed,'replay_failed':63-passed,'manuscript_sha256':h},ensure_ascii=False))
if __name__=='__main__':main()
