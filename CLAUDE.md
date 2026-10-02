# Claude Code 接手入口

请首先读取并遵守 [AGENTS.md](AGENTS.md)，这是 Codex 与 Claude Code 共用的规则来源，不在此复制第二套规则。

然后阅读 [当前交接状态](PROJECT_STATUS.md)、最新 HANDOFF 和 [执行规程](RUNBOOK.md)。新题一律走题型族流程（RUNBOOK 第一、二节），使用现有题型族、检查器和格式，不因更换助手重新设计流程。

旧的逐题 AI 流程（Builder v0.3，按 packet 工作）已归档，只用于追溯旧运行。如实记录模型身份，无法确认时写 unknown，不声称使用 GPT 模型。不要仅运行合成 demo 后报告真实 QA 已完成。

开始前核对 Git 和本地运行是否齐全；结束前更新 PROJECT_STATUS.md、检查变更并按授权提交同步。完整 runs/ 不在 GitHub，新机器不能假定存在。具体边界和交接要求以 AGENTS.md 为准。


## 当前下一阶段任务

先读 [HANDOFF_2026-09-30.md](HANDOFF_2026-09-30.md)：项目目的与用户已做的决定、现状数字、数据来源路线、代码地图、标准流程与经验、待决事项与建议顺序。上一份 [HANDOFF_2026-09-24.md](HANDOFF_2026-09-24.md) 保留历史（第 7b 节审核体系设计仍有效）。实际进度以 PROJECT_STATUS.md 顶部为准。
