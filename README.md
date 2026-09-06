# Geometry QA Builder v0.1

这是一个调用 GPT‑6 Astra、把论文材料转成可追溯候选 QA 的研究原型。无需训练模型，不依赖 SciQAG 代码。它不是已验证的 benchmark，也不是已经安装的 Codex Skill。


## 固定流程

材料包 → evidence 证据提取 → tasks 任务识别与验证规划 → qa 出题 → review 模型审核 → 程序检查 → 候选表。

- `prompts/`：独立、可修改的阶段提示词。
- `config.json`：模型、推理强度、输出限制、每篇题量上限。
- `schemas/*.json`：机器可读输入输出契约，由 `python builder.py schemas` 导出。
- `builder.py`：材料导入、阶段运行、手动结果导入、核验、报告。
- `RUNBOOK.md`：供当前任务执行的固定操作规程。
- `tests/test_builder.py`：验证失败关闭、引用、数值和记录不可覆盖等关键逻辑。
- `examples/`：明确标记的合成软件测试材料，不是论文数据。

## 本版范围

输入是可定位的文本材料，可从 UTF‑8 txt/md 或文本型 PDF 导入。PDF 只提取文字，不读取图像、可靠重建表格或执行 OCR；缺失结构/图片必须排除相关题或补充材料，禁止凭图注猜结构。每篇主文与补充材料可多次传 `--source`。XYZ 坐标以 angstrom 为单位，通过 `--xyz` 附加。

本版不自动检索/下载文献、不做多模态等价性、不自动组装正式测试集、不计算量子化学性质、不执行模型生成的代码。明确支持 XYZ 距离及三点夹角核验；其他科学推断仅做证据与模型筛查，仍待领域抽审。无需强制每篇出题，0 题是有效结果。Design 只保留为候选任务，不生成正式题。

## 命令

需要 Python 3.10+。核心仅使用标准库；PDF 输入额外需要 `pypdf`。

```text
python builder.py schemas
python builder.py prepare --paper-id paper-001 --title "论文标题" --url "论文链接" --source paper.md --source supplement.txt --out inputs/paper-001.json
python builder.py prepare --paper-id paper-002 --title "论文标题" --url "论文链接" --source paper.pdf --xyz structure.xyz --out inputs/paper-002.json
python builder.py init --bundle inputs/paper-001.json --run runs/experiment-001
python builder.py next --run runs/experiment-001
python builder.py accept --run runs/experiment-001 --result stage-result.json --model gpt-6-astra
python builder.py report --run runs/experiment-001
```

`next` 生成下一阶段完整请求包；在当前任务按其内容生成 JSON，使用 `accept` 验证并导入。重复四次。请求包已经包含前序证据、输出 schema 和规则，无需手工拼提示词。

API 批量方式：先在自己电脑设置 `OPENAI_API_KEY`，然后：

```text
python builder.py run --run runs/experiment-001 --max-calls 4
```

会发起最多 4 次顺序 Responses API 请求。已有完整阶段跳过；中断、拒绝、不合法 JSON、引用错误均停止并保留失败结果。网络超时不自动重试，避免重复计费；显式重新运行才继续。每次独立请求，不向评审阶段传递隐藏思维过程。当前未配置密钥，因此交付时未做真实 API 联调。

批量多篇：对每个材料包使用独立 run 目录重复执行；v0.1 不自动并发。材料、配置、提示词、schema 和程序快照随 run 保存；现有 run 使用旧快照，改进后新建 run 比较。API 响应保存实际返回模型和 token usage；模型别名仍可能更新，记录模型名不等于严格确定性。

## 输出与质量边界

`report.json`、`candidates.csv`（Excel 可打开）和 `report.md` 记录每题状态。`pending_human_audit` 表示自动检查通过待人工审核；`needs_revision` 表示模型或程序发现问题；没有自动“科学认证”。`benchmark_ready` 恒为 false。空题集不会被统计为成功。

证据原句匹配只证明来源中有这句话，不证明科学正确；同一个 GPT‑6 的审核不是独立专家审核。请抽查通过与拒绝记录并保留人工判断。候选 CSV 不包含完整内部证据包，后者保留在阶段 JSON 中；不得把答案和内部原文结论直接喂给被测模型。

## 版本与后续实验

先跑 B（分阶段流程）。后续加 A（直接出题）和 C（更强结构验证），使用相同材料、模型及题量限制，比较盲审合格率、错误放行率、误删、成本和人工时间。本版未实现 A/C，不能声称已完成方法有效性比较。

公开文档核对于 2026-09-06：
- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/reference/typescript/resources/beta/subresources/responses/methods/create

相关方法参考（未复用代码）：SciQAG https://arxiv.org/abs/2405.09939；SPIQA https://arxiv.org/abs/2407.09413。
