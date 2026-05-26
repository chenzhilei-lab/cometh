# Session Log — 2026-05-26

## Versions: V35 → V36 → V37 → V38

### V35 (5项方法学整改, 34pp)
- 速度对比公平性: 2列→3列硬件归一化表 (CPU-Trad/CPU-DL/GPU-DL)
- 2I/Borisov Type A(文献对比)/Type B(同数据) 结构分离, Table 16标题修复
- OOD检测器统计推导: 列联表+10%阈值trade-off+独立性假设显式声明+真实条件3因素
- 物理约束实现: 8步算法伪代码 (figure*)
- 复现性种子规格表
- BibTeX编译修复 (53引用全部解析, 0个(?)残留)
- 算法框图 figure* 全宽修复
- KPI表前新增Interpretive warning + 表注释首句加粗caveat
- 基线对比局限性诚实承认 + 管线集成路径讨论
- 消费者硬件推理基准表 + 小研究组操作指南
- OOD检测器语言降级: "可靠性保障"→"合成验证下的概念演示"
- 7个性能表标题统一标注 "(Synthetic Benchmarks Only)"

### V36 (语言简洁性, 35pp)
- 摘要紧缩~15%
- 全局"post-hoc"(7处)、"We emphasize that"(4处)、"published literature values"(8处)移除
- Stress Test 5 Construction 紧缩~40%
- PSE概念框新增
- 13个节标题精简

### V37 (A&C期刊精简版, 34pp)
- 超参数搜索表引用精简 (附录A)
- 种子表三处引用精简 (附录B)
- FLOPs分解表 → 附录C
- 消费者硬件表 → 附录D (标注"未实测仅供参考")
- 跨组件消融表 → 删除(替换为11行文字摘要)
- 操作指南压缩移除
- CO/CO₂区别去重 (三处重复→§3.3.5一处)
- §3.4可视化描述删除 (补一句repository引用)
- 消融表极端变体 (3×3/7×7 only) → 附录E
- KPI表0.4%加警示 + 球形晶粒校正表 → 附录F/G
- §2.6独立性讨论 ~300词→~70词 (扩展讨论 → 附录H)
- §5.7 Explicit Non-Claims 压缩~50%
- 附录重组: \appendix + 8个\section{} (A-H)

### V38 (全篇冗余精简, 34pp)
- "not a statistical validation" → "not statistical validation" (7处)
- "N=1 feasibility demonstration only" → "N=1 only; see §1.6" (4处)
- 冗长"No claim of real-data accuracy..." → 短句 (2处)
- Hale-Bopp解释 25词→6词
- §5.1 caveat段落 250词→120词

## 当前状态
- **最新版本**: `main_methodology_v38.tex/.pdf` — 34pp, 0 errors
- **Git**: main分支, 最新提交 `8820259`
- **剩余**: COMETH PINN vs Afρ same-data对比训练 (待RTX 3090)
