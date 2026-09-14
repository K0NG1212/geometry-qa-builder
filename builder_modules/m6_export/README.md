# M6 · 导出与记录

把模型可见输入与内部答案分开，并保留本轮检查报告。

- 状态：候选导出已实现。
- 执行方式：程序。
- 输入：完整通过流程的运行记录。
- 输出：model-inputs.json、private-answers.json、quality-report.json。

## 工作原理

白名单选取模型输入字段，清理 XYZ 注释，单独导出答案与检查限制。

## 检查与边界

阶段完整、导出格式、公开输入不包含内部答案字段。

还没有正式 benchmark 划分、跨论文去重或批调度；输入文字泄漏仍需审核。

## 单独优化

优化字段和数据划分策略；新增导出目标不应修改上游题目。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础格式验证和旧版兼容检查仍在 builder.py；调度在 pipeline.py。
改字段契约时要一起调整消费此字段的下游模块并新建 run，不能假定完全无依赖。

```text
python -m unittest discover -s tests -p test_m6_export.py -v
```
