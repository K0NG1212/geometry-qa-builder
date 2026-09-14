# M4 · 构题与计算

AI 描述题目和原子选择，程序产生几何数值答案。

- 状态：距离 / 夹角已实现。
- 执行方式：AI 计划 + 可信程序。
- 输入：构题计划、XYZ、单位依据。
- 输出：qa.json、construction-receipt.json。

## 工作原理

模型不得填写数值答案；距离用欧氏距离，夹角用两向量夹角公式。

## 检查与边界

编号、单位、容差、任务关联；计算结果保留。

只支持两点距离与三点夹角；题干是否与编号一致要审核。文字推断仍是候选。

## 单独优化

新增计算器先加入已知答案测试，再扩展计划格式和提示词。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础格式验证和旧版兼容检查仍在 builder.py；调度在 pipeline.py。
改字段契约时要一起调整消费此字段的下游模块并新建 run，不能假定完全无依赖。

```text
python -m unittest discover -s tests -p test_m4_construction.py -v
```
