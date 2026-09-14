# M1 · 检索与材料整理

按目标寻找适用来源，取得可用原文、结构和答案依据，再整理成材料包。

- 状态：检索规程 + 材料程序。
- 执行方式：Codex 检索 + 程序整理。
- 输入：goal.json → 检索结果 → 已取得的原文和结构。
- 输出：sources.json（助手记录）+ bundle.json + asset-units.json。

## 工作原理与边界

Codex 按 retrieval.md 使用检索工具，记录来源和取得情况；module.py 处理本地文本/XYZ及单位检查。只有论文列表不能交给下游构题。

程序检查：文本非空、XYZ 格式、单位原句与来源身份。

尚未完成：尚无自动检索器/下载队列；检索由 Codex 会话执行。OCR、可靠表格解析和检索覆盖率检查尚未实现。

## 怎么看输入输出

实际记录：sources.json（目前由助手保存）；bundle.json；asset-units.json。
运行 python tools/inspect_run.py --run 对应目录 --html，展开本地记录。
公开网站上的示例仅用于解释；目标/检索记录当前由助手保存，并非程序自动产物。

## 单独优化

优化解析和结构格式支持；先测试来源定位不丢失。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础校验和旧版兼容检查在 builder.py；调度在 pipeline.py。
修改字段契约要同时检查下游，新建 run 保留旧版本。

```text
python -m unittest discover -s tests -p test_m1_materials.py -v
```

目标驱动检索按 retrieval.md 由 Codex 执行；module.py 不自动联网。
