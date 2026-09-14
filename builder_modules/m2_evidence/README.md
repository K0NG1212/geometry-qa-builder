# M2 · 证据提取

从科学材料中提取能支持构题的证据单元，保留条件和限制。

- 状态：AI 协议 + 检查已接通。
- 执行方式：AI + 程序。
- 输入：材料包。
- 输出：evidence.json。

## 工作原理

Codex 读取独立提示词；程序检查输出格式、原句和资产引用。

## 检查与边界

唯一证据编号、原文匹配、结构资产存在。

未测真实论文提取准确率；原句存在不代表它支持模型归纳的结论。

## 单独优化

优先修改 prompt.md；用相同材料比较漏提、误提和不当推断。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础格式验证和旧版兼容检查仍在 builder.py；调度在 pipeline.py。
改字段契约时要一起调整消费此字段的下游模块并新建 run，不能假定完全无依赖。

```text
python -m unittest discover -s tests -p test_m2_evidence.py -v
```
