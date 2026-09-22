# M5 · 质量筛查

逐题检查输入、证据、几何必要性、泄漏、条件与评分标准。

- 状态：基础筛查已实现。
- 执行方式：AI 审核 + 程序。
- 输入：候选 QA、原始证据、AI 审核结果。
- 输出：review.json、report.json / md / csv。

## 工作原理与边界

独立目录中的程序汇总布尔检查、数值复算和当前 run 的完全重复项。

程序检查：审核覆盖完整；任一检查失败进入 needs_revision。

尚未完成：同一会话审核不是独立或专家审核；没有专家一致率、模型难度或语义去重实验。

## 怎么看输入输出

实际记录：review.packet.json → review.json 的 data；report.json。
运行 python tools/inspect_run.py --run 对应目录 --html，展开本地记录。
公开网站上的示例仅用于解释；目标/检索记录当前由助手保存，并非程序自动产物。

## 单独优化

完善错误类型与检查器；用正负样本测误放行和误拒绝。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础校验和旧版兼容检查在 builder.py；调度在 pipeline.py。
修改字段契约要同时检查下游，新建 run 保留旧版本。

```text
python -m unittest discover -s tests -p test_m5_quality.py -v
```


## 2026-09-22 几何依赖检查
真实新运行必须提供 geometry_audit，字段见 schema.json 与 prompt.md。程序检查记录完整性及判断与通过标志是否矛盾；不能自动判断科学语义是否正确。旧运行用冻结脚本，不能回填伪造历史。测试：`python -m unittest discover -s tests -p test_geometry_audit.py -v`。


## 第五次会议：按题型复用
方法层采用定义→构造→验证，见 [METHODOLOGY](../../METHODOLOGY.md)。[题型注册表](../../templates/registry.json) 和 [批量入口](../../template_engine.py) 已用两类数值模板运行12份既有结构。此入口独立于旧运行的严格格式；未自动更新题库。网站 templates.html 可查看实际输入、答案、核验和代码。
