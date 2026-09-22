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

## 力—位移补充计算器（Q02）

force_projection.py 接受同一原子顺序、同一坐标系中的 A/B 坐标和 B 处力，检查单位与非零位移，计算全原子力—位移点积和方向导数。它是显式调用的补充计算器，尚未加入通用 construction 的 verifier 分派；QNP001 的解释题沿用 evidence_review，不能把语义答案称为自动评分通过。tests/test_force_projection.py 验证正负号、近零、平移不变性与无效输入拒绝。QNP001 另外采用 Decimal 算术复核真实数据。


## 第五次会议：按题型复用
方法层采用定义→构造→验证，见 [METHODOLOGY](../../METHODOLOGY.md)。[题型注册表](../../templates/registry.json) 和 [批量入口](../../template_engine.py) 已用两类数值模板运行12份既有结构。此入口独立于旧运行的严格格式；未自动更新题库。网站 templates.html 可查看实际输入、答案、核验和代码。
