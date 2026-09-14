# Geometry QA Builder v0.3

把科学材料转成有证据、可检查的候选 QA。**当前默认由 Codex 会话执行 AI 模块，不需要 API Key。**

[查看模块工作台](https://k0ng1212.github.io/geometry-qa-builder/builder.html) · [数据流与 benchmark 复用](DATAFLOW.md) · [开始使用](QUICKSTART.md) · [模块划分](builder_modules/README.md) · [执行规程](RUNBOOK.md) · [测试说明](TESTING.md) · [Research Atlas](https://k0ng1212.github.io/geometry-qa-builder/)

## 这一版解决什么

把构题过程拆成独立模块：范围配置 → 材料整理 → 证据提取 → 任务模板 → 构题与计算 → 质量筛查 → 导出。
每一步明确输入、输出、检查范围和失败原因。AI 按项目中固定的提示词工作；程序管理记录并核验。

- evidence / tasks / review：AI 输出经过格式、引用或关联校验后保存。
- construction：AI 指定题目、结构和原子编号；程序生成距离或夹角数值答案，禁止 AI 填入猜测数值。
- status / next：继续未完成模块，复用已通过的结果。
- fork：修改已通过阶段时建立新分支记录，原结果保留。
- export：候选模型输入与私有答案分开，仍需审核题干是否泄漏答案。

## 文件分工

| 文件 | 用途 |
|---|---|
| pipeline.py | v0.3 入口；不调用 API |
| builder_modules/ | 七个模块目录，各有代码、格式、说明；AI 模块另有提示词 |
| RUNBOOK.md | Codex 逐步执行说明，无需安装全局 Skill |
| builder.py、prompts/、schemas/、modules/ | 保留旧版核心、共用工具和兼容文件 |
| tests/ | 来源、计算、快照、续跑和失败路径测试 |
| tools/replay_demo.py | 无模型调用的合成软件回放 |
| docs/ | 独立维护的 GitHub Pages 研究展示网站 |

## 快速运行软件示例

Python 3.10+，核心仅使用标准库；PDF 文字提取另需 pypdf。

```text
python tools/replay_demo.py --run runs/demo-v03
python pipeline.py status --run runs/demo-v03
python -m unittest discover -s tests -v
```

该示例回放手写 synthetic fixture，不是模型生成实验，也不计入 benchmark。
处理真实材料请在 Codex 中打开项目，让助手按 [RUNBOOK](RUNBOOK.md) 执行。

## 科学与运行边界

固定提示词不保证每次 AI 输出一致。保存材料、程序、规则快照和已接受结果用于追踪；重生成使用新记录。
来源引文匹配不证明结论成立，数值检查不证明科学意义。同一会话的生成和审核不是独立专家验证。
当前可信计算器只有 XYZ 距离、夹角；其他文字推断待审，Design 暂不出正式题。
每条记录 benchmark_ready=false，后续仍需专家抽审、难度评测、去重和测试集划分。

本版不含自动文献检索、多模态解析或无限无人值守批量生成。API 是后续可替换的执行方式；
旧版 API 入口保留用于兼容，详见 [v0.1 文档](LEGACY-v01.md)，不代表账号已获得对应模型权限。
运行目录 inputs/、runs/ 默认不进入 Git，避免把论文全文和内部答案随代码发布。

研究网站与 Builder 共用仓库，但问题分类和网站布局不会决定程序是否通过验证。
网站从 main/docs 发布，维护方式见 [网站说明](docs/README.md)。
