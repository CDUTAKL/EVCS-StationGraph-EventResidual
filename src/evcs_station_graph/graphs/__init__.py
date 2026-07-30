"""统计关系图构建接口。

本模块构造站内充电单元之间的五类候选统计关系矩阵。所有矩阵仅使用
训练期数据计算，验证集和测试集不参与相关系数估计。

五类关系：
- ``current_event``：同一时间片内接入/离站事件的共现强度
- ``historical_event``：活跃会话变化及事件历史的联合相关性
- ``load_correlation``：训练期代理负荷的线性同步性
- ``temporal_profile``：节点日内平均负荷曲线的相似度
- ``fused``：以上四类的加权融合（受 ``smoothing`` 控制）

所有关系经过 top-k 稀疏化和对称归一化后作为图模型的边输入。
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
