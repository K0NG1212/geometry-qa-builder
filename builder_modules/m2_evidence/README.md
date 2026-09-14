# M2 · 证据提取

从科学材料中提取能支持构题的证据单元，保留条件和限制。

- 状态：AI 协议 + 检查已接通。
- 执行方式：AI + 程序。
- 输入：已取得全文片段、结构与来源位置的 bundle，不是只有论文标题的列表。
- 输出：evidence.json。

## 工作原理与边界

Codex 读取独立提示词；程序检查输出格式、原句和资产引用。

程序检查：唯一证据编号、原文匹配、结构资产存在。

尚未完成：未测真实论文提取准确率；原句存在不代表它支持模型归纳的结论。

## 怎么看输入输出

实际记录：evidence.packet.json → evidence.json 的 data。
运行 python tools/inspect_run.py --run 对应目录 --html，展开本地记录。
公开网站上的示例仅用于解释；目标/检索记录当前由助手保存，并非程序自动产物。

## 单独优化

优先修改 prompt.md；用相同材料比较漏提、误提和不当推断。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础校验和旧版兼容检查在 builder.py；调度在 pipeline.py。
修改字段契约要同时检查下游，新建 run 保留旧版本。

```text
python -m unittest discover -s tests -p test_m2_evidence.py -v
```
