# 0.2.0 — 2026-09-14

- Added subscription-session pipeline, modular prompts, construction-plan and unit contracts.
- Numeric answers originate from trusted distance/angle code in the v0.2 path.
- Added context-bound imports, failure logs, status/resume, frozen runners and safe forks.
- Added separate candidate-input/private-answer exports and explicit screening limitations.
- Retained v0.1 core/API for compatibility; v0.2 makes no API calls.
- Added offline synthetic replay and failure-path tests; no scientific certification claimed.

# 版本记录

## 0.1.0 — 2026-09-06

- 固定 GPT‑6 Astra API 默认配置，四阶段提示词和 JSON 数据契约。
- 支持当前任务逐阶段导入及 Responses API 顺序运行。
- 支持 txt/md、文本型 PDF 和 XYZ 材料导入。
- 增加来源原句匹配、任务引用、完整审核覆盖、距离与夹角检查。
- 保存程序、提示词、配置和材料快照；禁止覆盖已有 run。
- 输出候选 CSV、JSON 与阅读报告，不自动认证或发布。
- 17 项离线测试通过；提供手写合成 fixture 演示。
- 未调用 GPT‑6 API（环境未配置密钥），未验证真实论文生成质量。

## 后续迭代建议

先用真实材料测试输入解析、引用与拒绝机制；再完善图像输入、结构对应和领域审核；最后进行 A/B/C 对照及跨论文组装。不要用合成测试 fixture 的通过率代表科学质量。
