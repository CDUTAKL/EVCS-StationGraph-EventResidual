# 图5-6视觉体系下的流程图重构记录（2026-09-22）

## 统一视觉规范

本轮以论文现有图5-6为唯一项目内风格锚点，并参考李芳凝论文流程图的版式语言：白色背景、浅蓝流程框、浅粉关键节点、极浅黄判断菱形、蓝色细虚线阶段区、黑色细正交箭头；中文采用宋体风格，数学符号采用Times风格。禁止渐变、阴影、图标、商业信息图、大色块和图内总标题。

本轮不是对上一版作局部换色，而是重新组织拓扑，重点消除“一字排开”、评价支路误串联、硬标签来源错误、事件标签参与部署路由等结构风险。

## 最终采用版本

| 图文件 | ImageGen源文件 | 核查重点 |
|---|---|---|
| `fig1_2_roadmap.png` | `exec-dc9718fd-7a75-4276-be59-e0173506f118.png` | 中央研究主轴、方法与诊断双翼、证据闭环 |
| `fig2_1_data_reconstruction.png` | `exec-a0e1cb56-a2d9-4354-a9ca-a74dbe26364e.png` | 重构漏斗、固定时间边界、训练/验证/测试职责分离 |
| `fig2_7_event_score_flow.png` | `exec-95cb3bc1-833e-49eb-b965-1fe6893cf6bb.png` | 四分量汇聚、训练统计、验证阈值、仅向未来扩展 |
| `fig2_10_dual_window_definition.png` | `exec-367dcc8c-258c-47dd-85df-a473db9c66ef.png` | 2×2交叉矩阵为中心，标签事件不驱动部署路由 |
| `fig3_8_train_predict_pipeline.png` | `exec-f004f924-0ad2-4ad2-bbed-0726e61399c1.png` | U形训练回路、早停反馈、六类评价并列而非串联 |
| `fig4_1_three_layer_framework.png` | `exec-07b372c6-6b50-4868-81ef-459401527d07.png` | 中央诊断主轴；教师产生软目标、真实标签产生硬目标 |
| `fig5_1_te_pcmci_flow.png` | `exec-f7ee5a9b-841e-440b-9d66-9e6d2a57cc79.png` | TE候选与PCMCI+核验分区，保留名义阈值与解释边界 |

旧版本保留于`outputs/figures/archive/2026-09-22-fig5_6-style-redraw/`，未删除。
