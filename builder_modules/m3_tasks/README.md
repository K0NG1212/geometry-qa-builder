# M3 · 任务模板

把证据转成可构题的任务模板，说明需要测什么、如何验证。

- 状态：AI 协议 + 检查已接通。
- 执行方式：AI + 程序。
- 输入：证据单元、原文与结构。
- 输出：tasks.json。

## 工作原理与边界

读取证据后判断适合测什么，规划具体输入、评分方法、领域、能力和双尺度；不只是划分能力标签。目标尺度与实例实际尺度分开记录。

程序检查：证据关联、资产可用、Design 不得误标为可直接出题。

尚未完成：模板科学意义、双尺度标签与几何必要性仍待研究审核。

## 怎么看输入输出

实际记录：tasks.packet.json → tasks.json 的 data。
运行 python tools/inspect_run.py --run 对应目录 --html，展开本地记录。
公开网站上的示例仅用于解释；目标/检索记录当前由助手保存，并非程序自动产物。

## 单独优化

优化任务识别提示词和可执行性检查；不为填满格子强行构题。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础校验和旧版兼容检查在 builder.py；调度在 pipeline.py。
修改字段契约要同时检查下游，新建 run 保留旧版本。

```text
python -m unittest discover -s tests -p test_m3_tasks.py -v
```


## 2026-09-22 几何依赖检查
真实新运行必须提供 geometry_audit，字段见 schema.json 与 prompt.md。程序检查记录完整性及判断与通过标志是否矛盾；不能自动判断科学语义是否正确。旧运行用冻结脚本，不能回填伪造历史。测试：`python -m unittest discover -s tests -p test_geometry_audit.py -v`。


## 第五次会议：按题型复用
方法层采用定义→构造→验证，见 [METHODOLOGY](../../METHODOLOGY.md)。[题型注册表](../../templates/registry.json) 和 [批量入口](../../template_engine.py) 已用两类数值模板运行12份既有结构。此入口独立于旧运行的严格格式；未自动更新题库。网站 templates.html 可查看实际输入、答案、核验和代码。
