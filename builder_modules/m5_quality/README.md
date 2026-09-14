# M5 · 质量筛查

逐题检查输入、证据、几何必要性、泄漏、条件与评分标准。

- 状态：基础筛查已实现。
- 执行方式：AI 审核 + 程序。
- 输入：候选 QA、原始证据、AI 审核结果。
- 输出：review.json、report.json / md / csv。

## 工作原理

独立目录中的程序汇总布尔检查、数值复算和当前 run 的完全重复项。

## 检查与边界

审核覆盖完整；任一检查失败进入 needs_revision。

同一会话审核不是独立或专家审核；没有专家一致率、模型难度或语义去重实验。

## 单独优化

完善错误类型与检查器；用正负样本测误放行和误拒绝。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础格式验证和旧版兼容检查仍在 builder.py；调度在 pipeline.py。
改字段契约时要一起调整消费此字段的下游模块并新建 run，不能假定完全无依赖。

```text
python -m unittest discover -s tests -p test_m5_quality.py -v
```
