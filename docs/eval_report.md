# clause-scope 评测报告（虚构标注样例）

> 评测生成：2026-09-18 · 对应 commit `fb05788`（round-2）· 样例：3 份虚构标注合同 / 25 条款 · 复现命令见仓库 README

| 指标 | 结果 |
|---|---|
| 条款分类准确率 | 100.0%（25/25） |
| span 回跳有效率 | 100.0%（25/25） |
| 风险检出率（召回） | 100.0%（4/4） |
| 风险提示精确率 | 80.0%（4/5；已知假阳性来源：条件解除权（如「甲方有权解除」）会被计为单方解除，区别于「任意解除」的细分属 v0.2） |

> 样本为 3 份**完全虚构**的演示合同（25 个条款），仅验证规则引擎行为；
> 真实合同（≥30 份、字段准确率 ≥85% 验收门）待语料到位后另行评测。

- contracts/sample_contract.txt：8/8 条款分类正确，检出 ONE_SIDE_RELEASE、VAGUE_JURISDICTION
- sample_data/contract_b.txt：7/7 条款分类正确，检出 MISSING_LIABILITY、ONE_SIDE_RELEASE、VAGUE_JURISDICTION
- sample_data/contract_c.txt：10/10 条款分类正确，检出 无
