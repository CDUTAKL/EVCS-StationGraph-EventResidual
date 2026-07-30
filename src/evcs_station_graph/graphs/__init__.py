"""统计关系图构建接口。

本模块构造站内充电单元之间的五类候选统计关系矩阵。所有矩阵仅使用
训练期数据计算，验证集和测试集不参与相关系数估计。

三类关系（独立存储，不预先融合——图模型通过可学习权重在消息传递中融合）：
- ``load``：历史负荷相关性 max(corr, 0)——负荷曲线越同步边权越大
- ``event``：充电行为共现余弦相似度——接入/离站/活跃变化模式相似性
- ``pattern``：时间模式指数核距离——日内平均负荷轮廓形状相似性

所有关系经过 top-k 稀疏化、对称化和对称归一化后作为图模型的边输入。
"""

from evcs_station_graph.graphs.relations import (
    RelationSet,
    build_relation_set,
    normalize_adjacency,
    sparsify_top_k,
)

__all__ = [
    "RelationSet",
    "build_relation_set",
    "normalize_adjacency",
    "sparsify_top_k",
]
