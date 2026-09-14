# 新版 Builder 怎么用

这是 v0.2 的日常入口。你不需要 API Key，也不需要手动复制各阶段提示词。
在 Codex 中打开这个仓库，提供材料目录，然后说：

> 阅读 RUNBOOK.md，按 v0.2 处理指定材料。已有 run 就先查看进度再继续；没有则创建新 run。
> 使用当前可用模型，记录真实执行方式。保存每个模块的证据、输出和检查报告。

新对话也可以用这句话，但要指明已有 run 的路径。项目文件保存流程，聊天不是唯一记录。
这里没有自动安装 Skill；RUNBOOK 是执行入口，modules 是模块提示词，pipeline.py 是程序控制器。

## 你会看到什么

1. 材料清单：实际读到了哪些原文、结构、补充材料，哪些缺失。
2. evidence.json：可定位的证据原句及限制。
3. tasks.json：由证据支持的任务模板、双尺度、能力和验证方法。
4. construction-receipt.json：AI 构题计划；qa.json：程序计算后的题目和答案。
5. review.json：逐题筛查；quality-report.json：总体检查及失败记录概况。
6. model-inputs.json：候选题的模型输入；private-answers.json：单独保存的答案。

这些都是候选记录，不会因程序通过就变成正式 benchmark。人工审查、难度测试和划分仍在后面。

## 先体验流程（纯软件示例）

在仓库根目录，Python 3.10+：

```text
python tools/replay_demo.py --run runs/demo-v02
python pipeline.py status --run runs/demo-v02
```

示例使用公开的手写 synthetic fixture，回放四阶段并生成一题距离答案。
**没有调用 AI，也不证明真实论文上的科学质量。** 已存在的 run 不会覆盖，换新目录再运行。

## 真实材料的操作由 Codex 执行

```text
python builder.py prepare --paper-id paper-001 --title "Paper title" --url "Original source URL" --source paper.md --xyz structure.xyz --out inputs/paper-001.json
python pipeline.py init --bundle inputs/paper-001.json --units inputs/paper-001.units.json --run runs/paper-001-v02
python pipeline.py next --run runs/paper-001-v02
```

units 文件格式见 examples/v02/asset-units.json。source_id 必须对应此材料包，引用要来自本包原文。
不知道单位时不填确认；init 可省略 --units，但数值构题会因单位未确认而停止。
不得把测试示例的单位说明复制成真实材料依据。角度虽无长度单位，当前实现也要求已确认的同单位 XYZ。

next 输出 packet 路径和 context 哈希。Codex 读取 packet，按其中规则生成 JSON，并保存到草稿文件；然后：

```text
python pipeline.py accept --run runs/paper-001-v02 --result inputs/evidence-result.json --model gpt-6-astra --context <next输出的context>
```

model 是如实记录的会话模型名称，不会切换模型。无法确认时写 unknown，并告知用户。
重复 next → AI 生成 → accept，依次完成 evidence、tasks、construction、review。
construction 输入不允许提供数值答案；受信任程序计算距离和夹角。文字推断答案保留待审。

```text
python pipeline.py export --run runs/paper-001-v02
```

## 失败、续跑和改版

- 当前模块失败：看 attempts-v02 中错误，修正该模块结果后再次 accept。前序输出保留。
- 中断后继续：status 找进度，再 next；已通过的输出不会重新生成。
- 修改已通过的构题：fork 原 run，原件保持可追溯。

```text
python pipeline.py fork --run runs/paper-001-v02 --target runs/paper-001-revision --before construction
```

fork 复用原有证据、任务和规则快照，清除新副本的构题及后续输出。历史失败记录随副本继承。
如改变提示词、规则或代码，应新建 run，从原材料重新运行，才能比较版本差异。
项目代码更新后，可用旧 run 内 pipeline_snapshot.py 执行旧流程。

提示词固定不等于生成内容相同。可复现的是材料/规则版本、已保存结果和确定性计算过程；
重新调用模型可能得到不同证据或措辞，因此保留新旧记录，不能覆盖后假称一致。
