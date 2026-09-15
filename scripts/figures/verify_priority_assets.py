"""File-level validation and compact link index for the sixteen reviewed figures."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
FIG=ROOT/'outputs/figures'
SPECS=[('2-3','fig2_3_load_heatmap','连续四周节点负荷'),
('2-5','fig2_5_weekly_curves','典型周负荷曲线'),
('2-8','fig2_8_event_hourly','标签事件日内分布'),
('2-10','fig2_10_dual_window_definition','双事件口径'),
('2-12','fig2_12_weekday_hour_heatmap','星期—小时负荷'),
('3-1','fig3_1_mrggcn_architecture','MRG-GCN整体架构'),
('3-2','fig3_2_relation_propagation_unit','多关系门控传播'),
('3-3','fig3_3_temporal_skip_fusion','时间编码与跨层融合'),
('3-4','fig3_4_lre_construction','LRE三关系构建'),
('3-11','fig3_11_bootstrap_difference','点级Bootstrap误差差'),
('3-13','fig3_13_mae_by_node','逐节点MAE'),
('4-5','fig4_5_residual_distribution','残差分布'),
('4-6','fig4_6_error_vs_event_intensity','事件分数与误差'),
('5-3','fig5_3_asymmetry','双向TE不对称性'),
('5-5','fig5_5_pcmci_validation_network','PCMCI+核验结果'),
('5-6','fig5_6_conformal_method','分层共形方法')]
GEN={'2-10','3-1','3-2','3-3','3-4','5-6'}

def main():
    rows=[]
    links=['# 16幅订正图查看索引','',
           '数据图与本轮四幅重绘图提供SVG与1200DPI PNG；4幅历史ImageGen示意图仍为原生PNG。旧稿未删除。','',
           '| 图号 | 内容 | PNG | SVG |','|---|---|---|---|']
    for num,stem,title in SPECS:
        png=FIG/(stem+'.png')
        with Image.open(png) as im:
            im.verify()
        with Image.open(png) as im:
            dims=im.size;dpi=im.info.get('dpi')
        assert min(dims)>700,(stem,dims)
        svg=FIG/(stem+'.svg')
        if num not in GEN:
            ET.parse(svg)
            assert dpi and min(dpi)>1199,(stem,dpi)
        else:
            assert not svg.exists(),'Stale SVG beside native raster: '+stem
        rows.append({'figure':num,'stem':stem,'size':dims,'dpi':dpi,
                     'sha256':hashlib.sha256(png.read_bytes()).hexdigest(),
                     'method':'ImageGen' if num in GEN else 'Matplotlib'})
        vector='—' if num in GEN else f'[查看]({svg})'
        links.append(f'| 图{num} | {title} | [查看]({png}) | {vector} |')
    out=FIG/'priority-review-20260907'
    (out/'asset_checks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    (ROOT/'docs/thesis/figure-priority-links-20260909.md').write_text('\n'.join(links)+'\n')
    print('16 PNG decoded; 10 SVG parsed; 10 data PNGs at1200dpi; 6 raster-only assets')

if __name__=='__main__':main()
