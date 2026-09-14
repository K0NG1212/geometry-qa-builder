# M1 · 材料整理

把可读原文、结构和单位依据整理成后续模块能引用的材料包。

- 状态：文本 / XYZ 已实现。
- 执行方式：程序 + 来源核对。
- 输入：txt / md / 文本 PDF / XYZ、单位依据。
- 输出：bundle.json、asset-units.json。

## 工作原理

文字分段并记录位置；解析坐标；逐一核对单位引用。

## 检查与边界

文本非空、XYZ 格式、单位原句与来源身份。

没有自动检索、OCR、可靠表格解析；单位是否适用于该结构需要核对。

## 单独优化

优化解析和结构格式支持；先测试来源定位不丢失。

入口为 module.py，schema.json 为本模块契约；AI 模块另有 prompt.md。
共用底层文件读写、基础格式验证和旧版兼容检查仍在 builder.py；调度在 pipeline.py。
改字段契约时要一起调整消费此字段的下游模块并新建 run，不能假定完全无依赖。

```text
python -m unittest discover -s tests -p test_m1_materials.py -v
```
