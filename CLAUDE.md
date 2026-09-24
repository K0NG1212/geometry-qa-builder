# Claude Code 接手入口

请首先读取并遵守 [AGENTS.md](AGENTS.md)，这是 Codex 与 Claude Code 共用的规则来源，不在此复制第二套规则。

然后阅读 [当前交接状态](PROJECT_STATUS.md)、[原型要求](PROTOTYPE.md)、[运行规程](RUNBOOK.md) 和 [数据流](DATAFLOW.md)。使用现有模块、提示词和格式，不因更换助手重新设计 Builder。

RUNBOOK 中“Codex 执行”指助手会话按 packet 工作；你可以用当前 Claude Code 会话执行相同步骤，如实记录模型身份，无法确认时写 unknown，不声称使用 GPT 模型。不要仅运行合成 demo 后报告真实 QA 已完成。

开始前核对 Git 和本地运行是否齐全；结束前更新 PROJECT_STATUS.md、检查变更并按授权提交同步。完整 runs/ 不在 GitHub，新机器不能假定存在。具体边界和交接要求以 AGENTS.md 为准。


## 当前下一阶段任务

阅读 [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md)（2026-09-24）：用户最新重点是扩展感知、推断、设计选择的可复用题型覆盖，不再只围绕最大间距与Rg扩量。该文件是本轮任务书；实际进度以PROJECT_STATUS.md顶部为准。
