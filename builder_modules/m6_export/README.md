# M6 · 导出与候选入池

把模型可见输入与内部答案分开，并保留本轮检查报告。

- 状态：候选导出已实现。
- 执行方式：程序。
- 输入：完整通过流程的运行记录。
- 输出：model-inputs.json、private-answers.json、quality-report.json。

## 工作原理与边界

白名单选取模型输入字段，清理 XYZ 注释，单独导出答案与检查限制。

程序检查：阶段完整、导出格式、公开输入不包含内部答案字段。

尚未完成：目前只导出本批候选；跨批合并、统一全局池、跨论文去重和正式入池审核尚未自动实现。导出不等于正式发布。

## 怎么看输入输出

实际记录：model-inputs.json；private-answers.json；quality-report.json。
运行 python tools/inspect_run.py --run 对应目录 --html，展开本地记录。
公开网站上的示例仅用于解释；目标/检索记录当前由助手保存，并非程序自动产物。

## 单独优化

优化字段和数据划分策略；新增导出目标不应修改上游题目。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础校验和旧版兼容检查在 builder.py；调度在 pipeline.py。
修改字段契约要同时检查下游，新建 run 保留旧版本。

```text
python -m unittest discover -s tests -p test_m6_export.py -v
```
