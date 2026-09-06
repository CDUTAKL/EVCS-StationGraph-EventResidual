from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt


OUT = Path('/Users/xushuyuan/Documents/Codex/EVCS-StationGraph-EventResidual/outputs/thesis/开题报告_基于站内多关系图与机制诊断的充电节点短期负荷预测研究_修订版.docx')
OUT.parent.mkdir(parents=True, exist_ok=True)

TITLE = '基于站内多关系图与机制诊断的充电节点短期负荷预测研究'


def set_cell_shading(cell, fill='FFFFFF'):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd')
        tc_pr.append(shd)
    shd.set(qn('w:fill'), fill)


def set_cell_borders(cell, color='000000', size='4', inside=False):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn('w:tcBorders'))
    if borders is None:
        borders = OxmlElement('w:tcBorders')
        tc_pr.append(borders)
    for edge in ('top', 'left', 'bottom', 'right'):
        tag = qn(f'w:{edge}')
        el = borders.find(tag)
        if el is None:
            el = OxmlElement(f'w:{edge}')
            borders.append(el)
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), size)
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), color)


def set_cell_width(cell, width_mm):
    cell.width = Mm(width_mm)
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn('w:tcW'))
    if tc_w is None:
        tc_w = OxmlElement('w:tcW')
        tc_pr.append(tc_w)
    tc_w.set(qn('w:w'), str(int(width_mm * 56.7)))
    tc_w.set(qn('w:type'), 'dxa')


def set_table_width(table, widths_mm):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn('w:tblW'))
    if tbl_w is None:
        tbl_w = OxmlElement('w:tblW')
        tbl_pr.append(tbl_w)
    tbl_w.set(qn('w:w'), str(int(sum(widths_mm) * 56.7)))
    tbl_w.set(qn('w:type'), 'dxa')
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_mm:
        col = OxmlElement('w:gridCol')
        col.set(qn('w:w'), str(int(width * 56.7)))
        grid.append(col)
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            set_cell_width(cell, widths_mm[min(i, len(widths_mm) - 1)])


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement('w:tblHeader')
    tbl_header.set(qn('w:val'), 'true')
    tr_pr.append(tbl_header)


def set_row_cant_split(row, cant_split=False):
    tr_pr = row._tr.get_or_add_trPr()
    existing = tr_pr.find(qn('w:cantSplit'))
    if existing is not None:
        tr_pr.remove(existing)
    if cant_split:
        tr_pr.append(OxmlElement('w:cantSplit'))


def set_page(doc):
    for sec in doc.sections:
        sec.page_width = Mm(210)
        sec.page_height = Mm(297)
        sec.top_margin = Mm(25.4)
        sec.bottom_margin = Mm(25.4)
        sec.left_margin = Mm(20)
        sec.right_margin = Mm(20)
        sec.header_distance = Mm(15)
        sec.footer_distance = Mm(17.5)


def fonts(run, east='STSong', latin='Times New Roman', size=12, bold=False, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = latin
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.insert(0, rfonts)
    rfonts.set(qn('w:ascii'), latin)
    rfonts.set(qn('w:hAnsi'), latin)
    rfonts.set(qn('w:cs'), latin)
    rfonts.set(qn('w:eastAsia'), east)


def clear_paragraph(p):
    for child in list(p._p):
        if child.tag != qn('w:pPr'):
            p._p.remove(child)


def para_format(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=True, line=1.25, before=0, after=0):
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.first_line_indent = Pt(24 if first else 0)
    pf.keep_together = False
    pf.keep_with_next = False


def add_text(p, text, size=12, bold=False, italic=False, east='STSong', latin='Times New Roman'):
    run = p.add_run(text)
    fonts(run, east=east, latin=latin, size=size, bold=bold, italic=italic)
    return run


def add_body(container, text):
    p = container.add_paragraph()
    para_format(p)
    add_text(p, text)
    return p


def add_heading(container, text, size=12, bold=True):
    p = container.add_paragraph()
    para_format(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first=False, line=1.25, before=2, after=2)
    add_text(p, text, size=size, bold=bold)
    return p


def add_center(container, text, size=12, bold=False, before=0, after=0):
    p = container.add_paragraph()
    para_format(p, align=WD_ALIGN_PARAGRAPH.CENTER, first=False, line=1.0, before=before, after=after)
    add_text(p, text, size=size, bold=bold)
    return p


def add_cell_body(cell, text, first=True, bold=False):
    p = cell.add_paragraph()
    para_format(p, first=first)
    add_text(p, text, bold=bold)
    return p


def remove_initial_empty(cell):
    if cell.paragraphs and not cell.paragraphs[0].text:
        # Keep the required paragraph node. Removing it leaves some Word/WPS
        # table cells without a writable paragraph and breaks generation.
        clear_paragraph(cell.paragraphs[0])


def add_cover(doc):
    add_center(doc, '成 都 理 工 大 学', size=22, bold=True, before=22, after=4)
    add_center(doc, '博硕士研究生学位论文开题报告', size=26, bold=False, before=4, after=26)
    table = doc.add_table(rows=6, cols=2)
    set_table_width(table, [61, 61])
    vals = [
        ('院、系（所）名称', '核技术与自动化工程学院'),
        ('专业', '电气工程'),
        ('研究方向', '电力系统负荷预测'),
        ('导师', '杨小峰'),
        ('研究生姓名', '胥舒元'),
        ('学位级别', '专业学位'),
    ]
    for row, (left, right) in zip(table.rows, vals):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_borders(cell, color='BFBFBF', size='4')
        for cell, txt in zip(row.cells, (left, right)):
            remove_initial_empty(cell)
            p = cell.paragraphs[0]
            para_format(p, align=WD_ALIGN_PARAGRAPH.LEFT, first=False, line=1.0)
            add_text(p, txt, size=11)
    add_center(doc, '研  究  生  院  制  表', size=12, before=28, after=2)
    add_center(doc, '      年   月   日', size=11, before=0, after=0)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


BACKGROUND = [
    '电动汽车保有量和公共充电设施持续增长，充电负荷预测已从整站总量估计逐步延伸到站内充电单元和短时间尺度预测。对于运行人员而言，15 min尺度的节点级预测可以辅助识别站内负荷差异、安排短时监测，并为后续容量评估提供输入。与居民或工业负荷相比，充电需求更直接地受车辆接入、充电持续和离站等会话行为影响，单个节点的负荷序列具有间歇性、稀疏性和节点异质性。',
    '本文使用公开ACN-Data充电会话记录开展研究。原始数据记录会话的接入时间、断开时间、节点标识和总交付电量，而非连续电表功率。因此，本文先将会话总电量按会话覆盖的15 min时间片进行分摊，再按spaceID聚合为节点代理负荷。这里的“节点”是会话记录中的充电接口或车位级空间单元，节点代理负荷是会话数据重构的时间片电量，不等同于实时计量功率，也不对应配电网母线或线路节点。明确这一边界，是保证模型结论可解释和实验可复核的前提。',
    '会话数据重构后，站内不同节点的历史负荷、行为变化和日内轮廓并不完全同步。若只沿单节点历史序列建模，可能无法利用节点间的统计联系；若简单使用一张无语义区分的关系图，又难以说明不同关系的作用。本文据此分别从负荷耦合、行为共现和轮廓相似三个角度构建LRE三关系图，并在时间卷积编码的基础上设计多关系门控图卷积网络（MRG-GCN），使关系级权重和节点级信息保留机制能够在同一预测框架中工作。',
    '充电会话具有明显的零值占比和局部突变特征。测试预测键中，目标侧标签事件窗口约占1.43%，而由预测起点可见冻结规则触发的样本约占0.43%。两者分别用于事后分层评价和预测时路由，不能混为同一事件口径。事件窗口的误差可能被大量稳定样本的平均结果掩盖，因此，仅报告全局MAE不足以说明模型在困难窗口、不同节点和不同预测步长上的表现。',
    '现有工作通常以全局误差比较模型，模型解释也常停留在注意力或消融结果的观察层面。对于多关系图预测模型，还需要进一步回答三个问题：模型是否依赖学习到的关系分配；图结构带来的收益能否被所检纯时序学生吸收；总体误差主要由哪些样本构成。本文引入由L1干预归因、L2蒸馏验证和L3四格溯源组成的三层机制诊断协议（MDP），以可执行的对照和误差还原补充模型性能比较。',
    '本研究的理论意义在于，将站内节点的多类统计关系、时间表示和门控机制放入同一预测模型，并把结构分析与误差溯源组织为分层诊断流程。工程意义则限定为：在同类会话数据和相近数据口径下，为充电设施的短期负荷研判、节点关注排序和后续容量分析提供可复现的模型参考。由于数据为节点代理负荷，本文不据此推导配电网潮流、设备热稳定或在线控制结论。',
]


STATUS = [
    '电动汽车充电负荷预测研究大致经历了统计模型、传统机器学习和深度学习三个阶段。早期研究多从出行规律、充电概率和历史负荷出发，采用回归、近邻、支持向量回归、随机森林或ARIMA等方法。Majidpour等比较了会话档案与站端测量记录下的预测条件，说明数据采集方式会改变输入特征和预测任务。国内综述和相关研究也表明，特征工程、LSTM、GRU、CNN及其组合模型已成为充电负荷短期预测的常用技术路线。上述研究为本文设置传统基线和时序基线提供了依据。',
    '近年来，研究重点进一步转向多步预测、站点差异和概率预测。Unterluggauer等基于多个充电场所和充电事件比较15 min聚合负荷在不同场所、不同预测步长下的难度；Buzna等研究了充电站的分层概率负荷预测；相关工作还将天气、价格、出行需求和站点属性作为外部信息输入。已有成果说明，预测尺度、站点类型、样本稀疏性和信息可见性会共同影响模型效果，但会话记录重构的节点代理负荷仍需要独立说明其数据边界。',
    '图神经网络为多节点预测提供了统一的关系建模工具。GCN以邻接矩阵传播节点特征，GAT通过注意力分配邻居贡献，RGCN将消息传递扩展到多关系场景；STGCN和Graph WaveNet进一步将图传播与时间卷积结合，AGCRN则通过节点自适应参数和可学习图结构刻画节点差异。相关研究已经把时空图模型应用于交通流、居民负荷、区域负荷以及电动汽车充电负荷预测，表明跨节点信息能够作为时间序列建模的补充。',
    '充电负荷图建模仍存在三个需要谨慎处理的问题。第一，空间邻近、历史相关、行为共现和轮廓相似不等同于配电网物理拓扑；第二，关系图若由全时段统计量一次性构建，可能忽视节点行为的语义差异；第三，若用未来真实负荷、完整离站时间或目标事件标签构图和路由，就会破坏预测时点的信息约束。因此，本文把图边限定为历史数据估计的统计预测关系，统一在训练期构建关系矩阵，并单独记录可见规则和目标侧标签的用途。',
    '模型可解释性研究已经提出特征归因、注意力分析、参数干预、知识蒸馏和分层误差评价等工具。Lundberg等和Jain等的研究提示，权重或注意力的可视化不能直接等同于解释；Runge等的PCMCI+可用于条件独立意义下的时间依赖结构发现，但不自动提供物理因果结论；Vovk等和Lei等的工作为分布无关预测区间提供了方法基础。本文在这些方法启发下组织MDP，并将第5章的方向性候选、共形区间和参数敏感度定位为探索性分析，不把它们表述为已经实现的事件预测部署方案。',
    '综上，现有研究已经在充电负荷预测、时空图建模和概率预测方面形成了较成熟的技术基础，但本文所针对的站内节点代理负荷仍有四点需要补充：一是从离散会话记录到节点级预测键的重构口径需要明确；二是站内多类统计关系需要区分构造并在模型中进行选择；三是模型结构证据、简化替代和误差来源需要形成可核验的诊断链；四是事件窗口的评价必须区分目标侧标签与预测时可见规则。本文围绕这四点组织研究。',
]


CONTENT = [
    '本研究的总体目标是：面向单站内充电节点代理负荷，建立一套数据口径清楚、信息使用受约束、模型结构可复核、诊断证据可追溯的短期预测方法。研究以15 min时间片为基础，以历史96步预测未来4步，在训练期构建LRE三关系图，在统一预测键上比较传统方法、时序模型和图模型，并用MDP三层协议解释模型内部关系分配、结构知识传递和误差样本构成。',
    '围绕总体目标，本文重点回答以下三个问题：（1）如何将离散会话记录重构为节点代理负荷，并在节点筛选、特征生成和事件定义中保持预测时点的信息边界；（2）如何将负荷耦合、行为共现和轮廓相似三类统计关系组织为可学习的多关系图卷积模型，以改善站内节点短期预测；（3）如何通过参数干预、知识蒸馏和四格误差溯源判断模型收益来自何处，并明确这些诊断结论的适用范围。',
    '研究内容一：会话数据重构、节点筛选与特征分析。研究采用31,424条公开充电会话记录，重构得到覆盖118,818个15 min时间步的节点代理负荷。以spaceID作为节点标识，设置训练、验证和测试三个时间段，筛选10个主分析节点，并保留15个节点作为敏感性分析集合。输入特征共7类，监督样本采用96步历史窗口和4步预测窗口，预测起点数量按时间顺序划分为83,103、17,807和17,809。',
    '节点筛选和归一化统计量只由训练期或验证期确定，测试集只用于冻结配置下的最终评价。样本构造阶段建立字段可见性清单：历史代理负荷、预测时点可见的行为状态以及日历和时段信息可以作为候选输入；未来真实负荷、完整离站时间、最终充电量和目标侧事件标签只能用于离线评价，不进入模型输入。本文将目标侧标签事件窗口与规则触发窗口分开记录，前者占测试预测键的1.43%，后者占0.43%。',
    '研究内容二：LRE三关系图与MRG-GCN预测模型。负荷关系由节点历史代理负荷的绝对Pearson相关构建，行为关系由接入、离站及活跃变化等行为信号的余弦相似度构建，轮廓关系由96步平均负荷轮廓的欧氏距离指数核构建。三类关系分别在训练期统计，经逐行Top-k保留、无向并集和对称归一化得到固定关系矩阵；本文的正式设置为k=5。关系边表示统计预测联系，不解释为物理拓扑或因果边。',
    'MRG-GCN以时间卷积网络为时间骨干，先从历史输入提取时间表示，再进行两层多关系图卷积。每层对三类关系分别完成加权消息聚合，由关系级β门控通过Softmax分配关系权重，再由节点级G门控调节邻居消息与自身表示的保留比例；两层使用独立的关系权重。第一层输出经残差MLP精炼后进入第二层，跨层融合只拼接H^(0)、H^(1)和H^(2)，最后经预测头输出未来4个时间步的10节点代理负荷。',
    '模型训练采用标准L1损失、AdamW优化器和早停策略，并在相同时间划分、预测键、归一化和评价程序下与Persistence、ARIMA、LightGBM、XGBoost、MLP、GRU、TCN、Graph WaveNet、AGCRN及AdaptiveGraph等模型比较。正式结果中，MRG-GCN全局MAE为0.01376 kWh/15 min，较TCN基线0.02952降低53.4%，较ARIMA基线0.02260降低39.1%。头部模型间不以“显著优于”作表述，结论以三种子均值、跨种子波动和统一评价口径为依据。',
    '研究内容三：三层机制诊断协议MDP。L1为干预归因层，观察两层β权重并对关系分配进行固定、等权和交换等参数替换，比较学习值与所检7种干预组合的误差响应，回答模型是否对当前关系分配存在功能依赖。L2为蒸馏验证层，以MRG-GCN为教师、TCN为学生，在给定学生结构、蒸馏目标和4个权重取值下重复训练，检验所检纯时序学生能否吸收图模型收益。L3为四格溯源层，以target_event和rule_trigger交叉分层，按样本量加权还原全局MAE，定位事件、稳定、误触发和漏触发样本对总体误差的贡献。',
    '研究内容四：模型结构分析与预测支持探索。第5章不新增第二套点预测方法，而是围绕主模型补充三类边界证据。第一，使用传递熵生成方向性候选，再用PCMCI+开展条件独立核验，结果定位为条件滞后依赖结构发现；第二，比较标准共形、冻结规则路由和标签事件事后参照，分析事件窗口经验覆盖率与区间宽度；第三，将关系级参数替换扩展到窗口和节点层面，描述分层参数干预敏感度。三类探索不解释为物理因果，也不承诺解决事件预测或直接形成在线控制方案。',
    '技术路线可概括为：公开会话记录→字段审计与时间清洗→节点代理负荷重构→训练/验证/测试时间切分→节点筛选与质量门禁→7特征监督样本构造→训练期LRE三关系图→TCN时间编码→双层MRG-GCN传播→跨层融合与4步输出→统一对比和消融→MDP三层机制诊断→第5章探索性结构与区间分析。每一步均记录输入、输出、数据边界和评价用途。',
    '在数据处理方面，本文以会话总交付电量和会话覆盖片数为基础，将会话电量分摊到所覆盖的15 min时间片，并按节点聚合。模型输入为历史96步、10节点和7特征，输出为未来4步；窗口不跨越训练、验证和测试切分边界。关系图只使用训练期统计量，规则阈值只由验证期冻结。全局评价采用MAE、RMSE和WAPE，并增加事件/稳定、负荷状态、节点和预测步长分层；不使用MAPE作为主指标，以避免高零值占比导致分母失真。',
    '在实验设计方面，正式模型和主要对照均采用三个随机种子，报告均值和跨种子标准差；确定性传统基线按同一预测键和物理量纲评价。消融实验区分结构拆除、关系子集、Top-k和关系随机失活等设置，不将复合变体的结果误写为单变量因果结论。对需要解释的结果，优先给出实验操作、对照条件和结论边界。',
    '在风险控制方面，重点关注代理负荷与真实计量功率不一致、事件窗口稀疏、关系统计随时间变化、规则触发与目标事件错位以及模型差异受随机种子影响等风险。应对措施包括：在正文中固定代理负荷边界；报告时间跨度、节点数和样本量；冻结构图和规则；采用三种子重复与成组Bootstrap描述不确定性；对失败或未达到正式纳入标准的探索保留完整记录，但不将其包装为方法贡献。',
    '本研究的特色与创新之处主要包括三点。第一，围绕会话记录重构的节点代理负荷建立可追溯的数据与评价口径，将节点可见性、事件双口径和分层评价写入统一实验协议。第二，构建LRE三关系图和MRG-GCN，通过关系级β门控、节点级G门控、逐层关系选择和跨层融合完成站内多关系信息传播。第三，构建MDP三层机制诊断协议，把关系分配干预、知识蒸馏验证和四格误差溯源组织为有操作、有对照、有边界的诊断链。这里的“构建”指本文对诊断流程的组织与验证，不把单个分析工具表述为首创。',
    '前期研究已经完成公开会话数据的字段审计、节点映射、时间网格重构、主分析节点筛选和监督样本构造；完成LRE三关系图、TCN时间骨干和MRG-GCN模型实现；完成传统基线、时序基线、图模型和自适应图对照，以及主要结构消融和多种子核验。初步结果显示，MRG-GCN全局MAE为0.01376 kWh/15 min，较TCN降低53.4%，说明该研究路线具有可实施的工程基础。',
    '实验环境具备GPU训练、CPU结构分析和文档整理条件，软件包括Ubuntu 22.04、Python 3.12、PyTorch 2.8.0、CUDA 12.1、NumPy、pandas、LightGBM和matplotlib等。研究代码已按数据、关系构建、模型、训练、评价和实验登记分层组织，并对配置、随机种子、数据版本、预测键和结果摘要进行归档。公开数据的来源、许可和文件校验信息在论文和项目记录中分别说明。',
    '预期成果包括：（1）形成会话记录清洗、节点代理负荷重构、节点筛选和信息可见性审计流程；（2）形成LRE三关系图和MRG-GCN节点短期负荷预测模型，给出统一对比、消融和敏感性结果；（3）形成由L1干预归因、L2蒸馏验证和L3四格溯源构成的MDP机制诊断材料；（4）形成方向性结构、预测区间和分层参数敏感度的探索性分析；（5）完成学位论文、开题及答辩材料，并保留代码、配置、随机种子、结果摘要和图表等可复核产物。',
]


def add_main_form(doc):
    table = doc.add_table(rows=0, cols=2)
    set_table_width(table, [30, 130])
    def row2(left, right, size=11):
        cells = table.add_row().cells
        for c in cells:
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_borders(c, color='000000', size='4')
        for c, txt in zip(cells, (left, right)):
            remove_initial_empty(c)
            p = c.paragraphs[0]
            para_format(p, align=WD_ALIGN_PARAGRAPH.CENTER, first=False, line=1.0)
            add_text(p, txt, size=size)
        return cells
    row2('论文题目', TITLE, size=11)
    row2('课题类型', '其他', size=11)
    row2('课题来源', '项目研究', size=11)
    label = table.add_row().cells[0]
    merged = table.rows[-1].cells[0].merge(table.rows[-1].cells[1])
    set_cell_borders(merged, color='000000', size='4')
    remove_initial_empty(merged)
    p = merged.paragraphs[0]
    para_format(p, first=False, line=1.0)
    add_text(p, '选题依据（简述课题的研究意义、国内外研究现状及发展趋势）', size=11)
    content = table.add_row().cells[0].merge(table.rows[-1].cells[1])
    set_cell_borders(content, color='000000', size='4')
    remove_initial_empty(content)
    for i, txt in enumerate(BACKGROUND):
        if i == 0:
            add_cell_body(content, '1、研究背景与研究意义', first=False, bold=True)
        add_cell_body(content, txt)
    add_cell_body(content, '2、国内外研究现状', first=False, bold=True)
    for txt in STATUS:
        add_cell_body(content, txt)
    label = table.add_row().cells[0]
    merged = table.rows[-1].cells[0].merge(table.rows[-1].cells[1])
    set_cell_borders(merged, color='000000', size='4')
    remove_initial_empty(merged)
    p = merged.paragraphs[0]
    para_format(p, first=False, line=1.0)
    add_text(p, '研究方案（包括：1、研究内容 2、研究方法及技术路线 3、特色与创新之处 4、研究基础和条件 5、预期成果）', size=11)
    content = table.add_row().cells[0].merge(table.rows[-1].cells[1])
    set_cell_borders(content, color='000000', size='4')
    remove_initial_empty(content)
    headings = {
        0: '1、研究内容',
        9: '2、研究方法及技术路线',
        13: '3、特色与创新之处',
        14: '4、研究基础和条件',
        16: '5、预期成果',
    }
    for i, txt in enumerate(CONTENT):
        if i in headings:
            add_cell_body(content, headings[i], first=False, bold=True)
        add_cell_body(content, txt)
    return table


def add_schedule(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    add_center(doc, '调查研究（或实验）及论文写作计划', size=12, bold=True, before=0, after=2)
    add_center(doc, '（2026年6月1日至2027年5月31日）', size=11, before=0, after=6)
    table = doc.add_table(rows=1, cols=6)
    widths = [10, 58, 22, 18, 29, 23]
    set_table_width(table, widths)
    headers = ['序号', '毕业论文工作阶段要求', '实习或出差', '地点', '起止日期', '检查方式']
    for cell, txt in zip(table.rows[0].cells, headers):
        set_cell_borders(cell, color='000000', size='4')
        remove_initial_empty(cell)
        p = cell.paragraphs[0]
        para_format(p, align=WD_ALIGN_PARAGRAPH.CENTER, first=False, line=1.0)
        add_text(p, txt, size=10.5)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    set_repeat_table_header(table.rows[0])
    rows = [
        ('1', '相关资料收集及文献查阅', '—', '校内', '2026.6—2026.7', '导师检查'),
        ('2', '技术路线及研究方案的确定', '—', '校内', '2026.7—2026.8', '导师检查'),
        ('3', '环境配置、代码编写及实验设计', '—', '校内', '2026.8—2026.9', '导师检查'),
        ('4', '进行实验和模型训练并不断迭代', '—', '校内', '2026.10—2026.12', '导师检查'),
        ('5', '实验数据记录和结论整理', '—', '校内', '2027.1—2027.2', '导师检查'),
        ('6', '撰写初稿', '—', '校内', '2027.2—2027.3', '导师检查'),
        ('7', '论文修改并送审', '—', '校内', '2027.3—2027.4', '导师检查'),
        ('8', '申请答辩', '—', '校内', '2027.4—2027.5', '导师检查'),
    ]
    for vals in rows:
        row = table.add_row()
        set_row_cant_split(row, True)
        for cell, txt in zip(row.cells, vals):
            set_cell_borders(cell, color='000000', size='4')
            remove_initial_empty(cell)
            p = cell.paragraphs[0]
            para_format(p, align=WD_ALIGN_PARAGRAPH.CENTER, first=False, line=1.0)
            add_text(p, txt, size=10.5)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    info = doc.add_table(rows=2, cols=2)
    set_table_width(info, [45, 115])
    for row, vals in zip(info.rows, [('预计初稿完成日期', '2027年3月'), ('计划定稿日期', '2027年3月')]):
        for cell, txt in zip(row.cells, vals):
            set_cell_borders(cell, color='000000', size='4')
            remove_initial_empty(cell)
            p = cell.paragraphs[0]
            para_format(p, align=WD_ALIGN_PARAGRAPH.CENTER, first=False, line=1.0)
            add_text(p, txt, size=10.5)
    doc.add_paragraph()
    add_heading(doc, '经费、设备、图书要求', size=11, bold=True)
    add_body(doc, '经费：由实验室课题组科研经费支持。')
    add_body(doc, '设备：实验室已有GPU计算设备及相关软件环境。')


def add_assessment(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    add_center(doc, '研究生作开题报告', size=12, bold=True, before=0, after=8)
    add_body(doc, '报告日期：               年      月       日')
    add_body(doc, '考评成绩：')
    add_center(doc, '□优秀  □良好  □合格  □不合格', size=11, before=4, after=8)
    add_body(doc, '考评小组成员签名：（成员由3—5人博导/硕导组成，学位论文开题考评小组设组长1名、秘书1名。导师不能担任考评小组组长）')
    for _ in range(4):
        add_center(doc, ' ', size=11, before=8, after=8)
    add_body(doc, '提出修改意见：')
    for _ in range(8):
        add_center(doc, ' ', size=11, before=8, after=8)
    add_body(doc, '导师意见：')
    for _ in range(5):
        add_center(doc, ' ', size=11, before=8, after=8)
    add_body(doc, '导师签名：')
    add_body(doc, '系（部）、教研室意见：')
    for _ in range(5):
        add_center(doc, ' ', size=11, before=8, after=8)
    add_body(doc, '系（部）、教研室主任签名：')
    add_body(doc, '学院意见：')
    for _ in range(5):
        add_center(doc, ' ', size=11, before=8, after=8)
    add_body(doc, '院长签名：')
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    add_heading(doc, '注：', size=10.5, bold=False)
    notes = [
        '1.研究生学位论文开题报告须先经导师审阅同意，书面报告的字数博士生不少于10000字，硕士生不少于5000字；',
        '2.此表请务必用A4幅面纸张双面打印对折；',
        '3.学位论文开题成绩不合格即为未通过开题。3个月后可重新申请开题。两次未通过者作分流处理；',
        '4.开题会相关材料由评审小组秘书负责汇总，并在会议结束后一周内将《学位论文开题报告》交所在培养单位。',
    ]
    for note in notes:
        add_body(doc, note)


def main():
    doc = Document()
    set_page(doc)
    # Normal style baseline; direct formatting below intentionally follows the source form.
    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'
    normal_rpr = normal._element.get_or_add_rPr()
    normal_rfonts = normal_rpr.rFonts
    if normal_rfonts is None:
        normal_rfonts = OxmlElement('w:rFonts')
        normal_rpr.insert(0, normal_rfonts)
    normal_rfonts.set(qn('w:ascii'), 'Times New Roman')
    normal_rfonts.set(qn('w:hAnsi'), 'Times New Roman')
    normal_rfonts.set(qn('w:eastAsia'), 'STSong')
    normal.font.size = Pt(12)
    add_center(doc, '学号：  2023050482', size=10.5, before=0, after=28)
    add_cover(doc)
    add_main_form(doc)
    add_schedule(doc)
    add_assessment(doc)
    doc.core_properties.title = TITLE + ' 开题报告'
    doc.core_properties.author = '胥舒元'
    doc.core_properties.subject = '专业学位硕士学位论文开题报告'
    doc.save(OUT)
    print(OUT)


if __name__ == '__main__':
    main()
