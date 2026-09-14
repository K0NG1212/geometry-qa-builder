# M4 · 构题与计算

AI 描述题目和原子选择，程序产生几何数值答案。

- 状态：距离 / 夹角已实现。
- 执行方式：AI 计划 + 可信程序。
- 输入：构题计划、XYZ、单位依据。
- 输出：qa.json、construction-receipt.json。

## 工作原理与边界

模型不得填写数值答案；距离用欧氏距离，夹角用两向量夹角公式。

程序检查：编号、单位、容差、任务关联；计算结果保留。

尚未完成：只支持两点距离与三点夹角；题干是否与编号一致要审核。文字推断仍是候选。

## 怎么看输入输出

实际记录：construction.packet.json；construction-receipt.json；qa.json 的 data。
运行 python tools/inspect_run.py --run 对应目录 --html，展开本地记录。
公开网站上的示例仅用于解释；目标/检索记录当前由助手保存，并非程序自动产物。

## 单独优化

新增计算器先加入已知答案测试，再扩展计划格式和提示词。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础校验和旧版兼容检查在 builder.py；调度在 pipeline.py。
修改字段契约要同时检查下游，新建 run 保留旧版本。

```text
python -m unittest discover -s tests -p test_m4_construction.py -v
```
