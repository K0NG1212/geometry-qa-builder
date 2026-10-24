# Claude Code 接手入口

请首先读取并遵守 [AGENTS.md](AGENTS.md)，这是 Codex 与 Claude Code 共用的规则来源，不在此复制第二套规则。

然后阅读 [当前交接状态](PROJECT_STATUS.md)、最新 HANDOFF 和 [执行规程](RUNBOOK.md)。新题一律走题型族流程（RUNBOOK 第一、二节），使用现有题型族、检查器和格式，不因更换助手重新设计流程。

旧的逐题 AI 流程（Builder v0.3，按 packet 工作）已归档，只用于追溯旧运行。如实记录模型身份，无法确认时写 unknown，不声称使用 GPT 模型。不要仅运行合成 demo 后报告真实 QA 已完成。

开始前核对 Git 和本地运行是否齐全；结束前更新 PROJECT_STATUS.md、检查变更并按授权提交同步。完整 runs/ 不在 GitHub，新机器不能假定存在。具体边界和交接要求以 AGENTS.md 为准。


## 当前下一阶段任务

先读 [HANDOFF_2026-10-24.md](HANDOFF_2026-10-24.md)：现状数字、本会话做了什么、下一条线的候选清单、必读经验。**一次只做一条线**（第 0 节），由用户从第 3 节挑一条。细节记录见 [HANDOFF_2026-10-21.md](HANDOFF_2026-10-21.md)。更早的 [HANDOFF_2026-10-19.md](HANDOFF_2026-10-19.md)：设计题路线① 的三条约束、偶氮苯反应路径三个新族、二面角病态的陷阱（**现状数字以 10-24 与 PROJECT_STATUS 顶部为准**）。各文件分工：证据题两族的形式与证据卡设计、子领域与旭日图见 [HANDOFF_2026-10-18.md](HANDOFF_2026-10-18.md)（第 3、4 节）；协作方式与判断原则、批量选题暂定规则见 [HANDOFF_2026-10-06.md](HANDOFF_2026-10-06.md)（第 9、5 节）；数据来源路线、代码地图与标准流程见 [HANDOFF_2026-09-30.md](HANDOFF_2026-09-30.md)；审核体系设计见 [HANDOFF_2026-09-24.md](HANDOFF_2026-09-24.md) 第 7b 节。实际进度以 PROJECT_STATUS.md 顶部为准。

## 历次组会记录（本地，不在 GitHub 上）

见 [AGENTS.md](AGENTS.md) 接手顺序第 4 条：`inputs/meetings/00-总索引与全梳理.md`。
