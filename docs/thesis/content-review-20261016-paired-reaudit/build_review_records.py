"""Serialize the principal review judgment and its paired evidence records.

The scores below are human-readable review judgments, not inferred by this code.
Run only after all three raw reviewer reports and recomputations are complete.
"""
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCOPE = '五章全文、双语摘要、结论、表格与图注；内容与证据；学校版式另审'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, obj):
    (HERE/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')


def normalized(v):
    return float((Decimal(str(sum(v)))/90*100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def main():
    reports=['reviewer-integrity.md','reviewer-methods.md','reviewer-literature-practice.md']
    assert all((HERE/p).is_file() for p in reports)
    assert json.loads((HERE/'primary-evidence-recomputation.json').read_text())['status']=='PASS'
    rubric=json.loads((HERE/'packet/rubric.json').read_text())
    specs=[
      ('B','packet/before-training.md','before','完整训练前稿'),
      ('A','packet/after-training.md','after','完整当前稿'),
      ('BCHK','packet/before-evidence/checkpoint-replay-report.md','before','60/63前向、3项旧AdaptiveGraph缺口与复核范围'),
      ('BLINK','packet/before-evidence/paper-mae-archived-audit.json','before','归档预测到论文数字的逐行审计'),
      ('BDATA','packet/before-evidence/data-availability.md','before','原数据身份及材料缺口'),
      ('NEAR','packet/after-evidence/nearest-work-original.md','after','最接近工作来源层级、已核查字段与未知字段'),
      ('NEAR2','packet/after-evidence/nearest-work-72-73.md','after','新增近邻摘要比较'),
      ('S31','packet/after-evidence/sg031-report.md','after','031合同、结果和解释边界'),
      ('S32','packet/after-evidence/sg032-report.md','after','032合同、目标及解释边界'),
      ('ADAPT','packet/after-evidence/adaptivegraph-report.md','after','匹配CUDA及固定邻接CPU回放报告'),
      ('MDP','packet/after-evidence/jpl-mdp-report.md','after','JPL L1/L3复核范围'),
      ('CAL','packet/after-evidence/jpl-calibration-report.md','after','JPL独立校准路径和分层结果'),
      ('QUALITY','packet/after-evidence/data-quality-report.md','after','目标效度和数据局限'),
      ('METHODRAW','methods-numeric-recompute.json','after','本轮18次运行逐键重算、训练合同/日志/哈希、周块区间及原始CSV目标重建'),
      ('PRIMARYRAW','primary-evidence-recomputation.json','after','本轮60份原始数组/预测文件：019、JPL MDP/校准及AdaptiveGraph的独立算术和哈希核验'),
      ('SOURCE','paired-source-audit.json','both','两稿图表/公式/引文及源图路径检查'),
      ('DIFF','manuscript-paired.diff','both','两稿逐行差异'),
    ]
    evidence=[]
    for ident,path,period,coverage in specs:
        p=HERE/path
        evidence.append({'id':ident,'path':path,'source':str(p.resolve()),'locator':path,
            'sha256':sha(p),'reviewed':True,'period':period,'scope':coverage})

    # Same anchors are applied anew to each time point; no historical score is inherited.
    before=[4.5,5,4,4.5,7.5,4,9,7.5,9,7,3,9]
    after =[4.5,5,4.5,4.5,8.5,4.5,9,8.5,9.5,8,3,9.5]
    locations=[
      '两稿§1.1–1.3、§2.1–2.3、§5.4.1',
      '两稿题名、摘要、§1.4–1.6、§3.8、§4.5、结论；后稿§4.6',
      '两稿§1.2、表1-1、参考文献[12]/[13]/[67]/[70]/[71]；后稿§1.2.2的[72]/[73]',
      '两稿式(2-1)、式(3-1)–(3-13)、§4.2.5、§5.2–5.4',
      '前稿§3.6–3.7、§4.3；后稿§3.7.2表3-11、§3.8.3表3-14、§3.8.4表3-15',
      '两稿§3.6.1/3.6.4；后稿表3-14、031/032合同与本轮原始数值核验',
      '两稿第2–5章；后稿§3.7.2/3.8.4/4.6/5.3.5',
      '前稿表3-2/3-3/3-9、§3.8；后稿表3-11/3-13/3-15、表4-7/4-8、§5.3.5',
      '两稿§3.6–3.8、§4.2.5/4.3.3/4.4.4、§5.2/5.3；后稿摘要/§4.6/结论',
      '两稿§1.2.2/1.4、§3.5.8/3.8.1、§4.5；后稿表3-11/3-13、§4.6、结论',
      '两稿§5.4.1–5.4.5、固定轨迹表及合成LP表、结论工程含义',
      '两稿双语摘要、§3.6–3.8、§5.3–5.5、结论及引文；后稿附录A',
    ]
    bwhy=[
      '站内稀疏和节点异质性有具体统计支持，研究对象与问题清楚；现场运行需求及经济损失没有量化。按问题定义评价给4.5，现场收益另在BR-11评价，不重复要求所有选题意义都由现场试验产生。',
      '题名中的机制诊断在正文定义为模型功能敏感度及误差分组，代理量、发布时点和协议范围始终明示；没有发现题目—研究问题—所检结论的实质错位。题名术语需要正文定义本身不是扣分证据。',
      '已比较六项直接/方法近邻，并记录可读来源与未知字段；但[72]/[73]只列入书目，遗漏多关系与门控时空方法的直接讨论，不能进入4.5强档。原文已知信息与不确定字段处理总体合理，给充分但有缺口的4。',
      '能量与功率单位、统计图、图传播、β与关系变换的重参数化、共形有限样本秩和时间依赖均讲解正确；未提供一般方法的推导扩展或真实计量模型，不将常规工具准确应用等同理论突破。',
      '行为输入、四段留窗、近容量TCN和同参数门控已形成合适基础；但单关系分支变更未识别逐关系条件增量，替代目标只有重构差而无模型重训，门控触顶及L2容量/输入/损失混淆仍在。设计总体合理，关键辨识缺口下给7.5。',
      '主要行为协议检查点链完整，63份归档预测到指标可算；三次旧AdaptiveGraph完整前向仍不匹配，后端选边解释尚待验证，且训练源码身份有缺口。60/63不能与全部模型权重可重放等同，给4。',
      '数据口径核查、多协议建模、受控门控、参数干预、蒸馏、分组误差、校准失败诊断与合成约束接口构成有难度的完整研究，达到9分强档。不按图表数、投入时长或训练次数加分。',
      '已有证据支持协议内总体及门控的有限结论，但三关系条件增量、目标定义敏感性尚无直接训练证据，MDP仅一站且L2控制不充分；这些是核心问题的实证覆盖缺口，尚不能按强证据档评分，给7.5。',
      '已区分种子、键与时间块，处理等权β、非零/事件反向结果、TE多重校正与事后分析，属于统计解释强档9；但困难组未在摘要主比较同等突出，门控训练上限与结论权限还未集中列清。',
      '节点门控有同参数实证，站内关系任务化和MDP判断组织提供可信组合增量；逐关系条件价值未识别，诊断指导改模收益未建立，图/门控/TCN本身有近邻先例。按有用增量给7。',
      '提供具体的时间映射、单位换算、失败轨迹与合成约束可行性检查；但真实案例因缺同步电表、设备/车辆约束和电价而不能形成计划。对应量表“价值合理但现场验证有限”的3分锚点；合成可行性不等于场站效益。',
      '全文可读、协议边界基本一致，重要指标可追溯；仍有[72]/[73]未引用、结果主次并置和重复限制段，不能计满分。它们是定位明确的局部组织/规范缺口，整体仍给9分。',
    ]
    awhy=[
      bwhy[0], bwhy[1],
      '新增[72]/[73]的Pearson/TE多关系和门控GCN/TCN先例，明确排除一般结构首创，补齐与当前贡献直接相关的近邻维度；不是要求重跑每个近邻才能写综述。部分全文协议仍未知，[67]会话重构先例亦宜补进表1-1，因此给4.5而非满分。',
      bwhy[3],
      '031保持三槽位及32714参数，同种子非邻接初值一致、只替换指定图并重训；032固定输入/图/键、改变目标并在新训练前缀重标定，两个主要替代解释现在有适当对照。仍缺更长门控预算、容量匹配AGCRN/行为GRU及匹配L2；032固定原图且只比较两模型。设计明显改善至8.5，尚未达到主要控制均充分的9分锚点。',
      '匹配CUDA及固定CUDA邻接CPU的三个AdaptiveGraph输出吻合原预测，特定后端失败疑点得到直接解释；031/032合同、原始CSV重构、18运行预测/日志/哈希和周块区间可复查。原训练Git身份及历史PCMCI+版本/矩阵等来源缺口仍在，给4.5，不把本轮数组重算冒称新CUDA前向或从头训练复现。',
      bwhy[6]+' 新增工作进一步证明针对问题的处理能力，但原稿已在9分强档；当前仍无额外独立数据或部署问题解决，维持9，不以新增运行数量跨半分。',
      '031两类邻接校正区间为正，032在另一代理目标上共同键排序保持，JPL L1/L3和独立校准实际完成，核心论证从部分配置观察推进到更多受控实证。已查看测试期、共享门控预算替代解释、第三关系不确定、非零/事件无全面优势、固定图敏感性和受限L2仍使确认范围有限。给8.5；诚实披露这些缺口不能自动使证据充分性进入9分。',
      '三项关系比较校正、旧事件/新零值分层区分、共享门控触顶、固定原图及测试期已查看的边界均进入核心叙事；JPL总体约90%仍事件不足被准确解释。本轮原始复算支持这些解释，给9.5。此项奖励解释可靠，不能被转记为未来期、实测或运行能力已经验证。',
      '新增两类邻接相对自环的同参数条件增量，是可检查的新经验知识；032扩展目标定义敏感性，JPL L1/L3使部分诊断判断在另一场站受检。与训练前相比从“多关系整体有用但各类不清”前进了一步，给8。仍是任务化、条件性增量；无一般算子首创、三关系均必要或诊断指导改模获益证据，不给强原创档。',
      bwhy[10]+' 032仍是会话代理目标，JPL校准仍未提供现场约束或实际收益，因此当前该项维持3。',
      '行为输入主结果及关键分层表前置、完整组件表移附录、031/032与JPL诊断/校准跨章节同步，摘要和结论更集中；92项均被引用，未发现未定义引用或重复图表/公式编号。仍有回溯结果篇幅和少量句子连接可压缩，故9.5不满分。Word版式及作者信息另审。',
    ]
    reasons=[
      '选题需求证据未变，新增训练不替代现场需求量化。',
      '两版本均已正确限定对象与结论范围；重组价值计入BR-12。',
      '[72]/[73]由未入文的书目转为具体近邻比较，增强缺口论证。',
      '基础概念及推导准确性未实质改变；032是实证敏感性而非新理论。',
      '031补逐邻接同参数控制、032补另一目标构造重训练；加分对应辨识设计改善。',
      'AdaptiveGraph三个旧前向缺口得到匹配CUDA/固定邻接证实；新合同与原始复算增强可追溯链。',
      '原稿已有足够难度和问题解决链；不按额外训练数直接加分。',
      '结果确实支持两类关系条件增量、替代目标排序和JPL诊断/校准，补齐原稿未受检结论。',
      '新增结果的终点、校正、分层、预算及事后性质进入主要结论，统计解释更完整。',
      '由关系整体/子集观察推进到两类邻接的受控新增经验知识，且MDP部分判断受跨站检验。',
      '无同步计量、真实运行约束或收益新证据，实践能力没有因新训练而增加。',
      '结果主次、跨章同步、摘要/结论压缩和引用闭合是可以检查的表达改善。',
    ]
    bref=[['B','BDATA'],['B'],['B','SOURCE'],['B'],['B'],['B','BCHK','BLINK'],['B','BCHK'],['B','BCHK'],['B'],['B'],['B','BDATA'],['B','SOURCE','DIFF']]
    aref=[['A','QUALITY'],['A'],['A','NEAR','NEAR2','SOURCE'],['A','S32'],['A','S31','S32','METHODRAW'],['A','ADAPT','METHODRAW','PRIMARYRAW'],['A','METHODRAW','PRIMARYRAW'],['A','S31','S32','METHODRAW','PRIMARYRAW'],['A','METHODRAW','PRIMARYRAW'],['A','S31','S32','MDP','METHODRAW'],['A','QUALITY'],['A','SOURCE','DIFF']]
    before_evidence=[e for e in evidence if e['period'] in ('before','both')]
    old=json.loads((ROOT/'docs/thesis/content-review-20261012-rev6/scorecard.json').read_text())
    packetid='EVCS-THESIS-PAIRED-20261016'
    def card(which,scores,whys,refs,ev):
        filename='before-training.md' if which=='BEFORE' else 'after-training.md'
        rows=[]
        for i,c in enumerate(rubric['criteria']):
            if which=='BEFORE':
                oldscore=old['criteria'][i]['score']
                typ='recalibration' if scores[i]!=oldscore else 'unchanged'
                why='本轮对同一训练前冻结稿重新套用原锚点；'+whys[i] if typ=='recalibration' else '按同一锚点复核后维持训练前该项评价。'
            else:
                typ='improvement' if scores[i]>before[i] else ('regression' if scores[i]<before[i] else 'unchanged')
                why=reasons[i]
            rows.append({'id':c['id'],'score':scores[i],'manuscript_location':locations[i],
              'evidence_ids':refs[i],'rationale':whys[i],'na_reason':None,
              'change':{'type':typ,'reason':why,'evidence_ids':refs[i]}})
        return {'schema_version':1,'rubric_id':rubric['rubric_id'],
          'assessment_id':f'FORMAL-20261016-PAIRED-{which}', 'assessment_kind':'formal',
          'review_date':'2026-10-16','confidence':'medium',
          'packet':{'packet_id':packetid+'-'+which,'manuscript_path':'packet/'+filename,
            'manuscript_sha256':sha(HERE/'packet'/filename),'scope':SCOPE,
            'scope_note':'同稿、同量表重新评估；三视角隔离但README有历史数字暴露；主评有历史上下文。科学内容与学校版式分开。',
            'evidence':ev},'reviewer_reports':reports,'forensic_report':'forensic-review.md',
          'criteria':rows,'blockers':[],
          'limitations':['三视角为隔离AI评阅而非现实专家；README含历史数字，不能称完全数值盲化。',
            '本轮从已保存数组与原始会话重算；未重新训练或新跑检查点前向。',
            '只抽查重要近邻原来源，没有重新认证92篇全文、全部历史基线或Word逐页视觉。',
            '正文的非零组、代理效度、事后固定期与现场收益限制仍成立。']}
    bc=card('BEFORE',before,bwhy,bref,before_evidence)
    ac=card('AFTER',after,awhy,aref,evidence)
    write('scorecard-before.json',bc);write('scorecard-after.json',ac)
    table=['| 项目 | 满分 | 训练前重审 | 当前稿重审 | 原始变化 |','|---|---:|---:|---:|---:|']
    for i,c in enumerate(rubric['criteria']):
        table.append(f"| {c['id']} {c['name']} | {c['maximum']} | {before[i]:g} | {after[i]:g} | {after[i]-before[i]:+g} |")
    table.append(f'| **合计** | **90** | **{sum(before):g}** | **{sum(after):g}** | **{sum(after)-sum(before):+g}** |')
    body='\n'.join(table)
    details=[]
    for i,c in enumerate(rubric['criteria']):
        details.append(f"## {c['id']} {c['name']}\n\n定位：{locations[i]}。\n\n训练前 {before[i]:g}/{c['maximum']}：{bwhy[i]}\n\n当前稿 {after[i]:g}/{c['maximum']}：{awhy[i]}\n\n变化依据：{reasons[i]}\n\n证据：{', '.join(bref[i]+aref[i])}。")
    (HERE/'scorecard.md').write_text('# 同量表配对重审评分表\n\n非官方内容模拟，量表EVCS-THESIS-CONTENT-1.0，原始90分。\n\n'
      f'当前稿 **{sum(after):g}/90＝{normalized(after):.2f}/100**；训练前同尺度重审 **{sum(before):g}/90＝{normalized(before):.2f}/100**。'
      f'修订效应为原始 **+{sum(after)-sum(before):g}/90**。这是同时重评两稿的差，不是从历史总分直接加分。\n\n'+body+'\n\n'+'\n\n'.join(details)+'\n\n'
      '证据ID详见scorecard-before.json和scorecard-after.json；独立视角、主评裁定与历史校准见forensic-review.md。'
      '学校版式、个人信息和暂缓占位另审；本分数不预测学校等级或优秀论文结果。\n')
    delta={'before_vector':before,'after_vector':after,'before_raw':sum(before),'after_raw':sum(after),
      'before_normalized':normalized(before),'after_normalized':normalized(after),'revision_effect_raw':sum(after)-sum(before),
      'old_before_raw':sum(x['score'] for x in old['criteria']),
      'before_calibration_effect_raw':sum(before)-sum(x['score'] for x in old['criteria'])}
    oldafter=json.loads((ROOT/'docs/thesis/content-review-20261016-rev8/scorecard.json').read_text())
    delta['old_after_raw']=sum(x['score'] for x in oldafter['criteria'])
    delta['after_calibration_effect_raw']=sum(after)-delta['old_after_raw']
    delta['decomposition']='原历史两稿差 + 当前稿校准差 - 前稿校准差 = 本轮配对修订效应；评分校准不称论文退步。'
    write('paired-score-delta.json',delta)
    print(json.dumps(delta,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
