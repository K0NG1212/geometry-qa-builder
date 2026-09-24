# 第五次会议后的方法：定义 → 构造 → 验证

本文件是当前方法入口；M0–M6 保留为可追溯实现细节，旧运行不改写。

| 方法步骤 | 复用单元 | 现有实现 |
|---|---|---|
| 定义 | 题型：考点、输入、输出、范围、验证函数与适用条件 | M0–M3；templates/registry.json |
| 构造 | 将模板应用到不同合格结构，程序生成短答案 | M4；template_engine.py 批量试跑入口 |
| 验证 | 全量数值检查；模板语义集中审查；按风险抽样实例 | M5–M6；verification.json，原 AI 检查仍可用于复杂模板 |

## 已实现的最小批量路线

最大间距、等权回转半径两类，共 12 份既有真实结构输入。所有计算都使用模板 ID 分派同一个函数；不按题号选择不同算法，也不从原答案生成新答案。保留旧参考数值仅作结果对比。

```text
python template_engine.py --manifest templates/pilot-manifest.json --out runs/template-pilot-new
python -m unittest discover -s tests -p test_template_engine.py -v
```

新输出目录包含：manifest.json（输入配置）、student-packets.json（学生包）、private-answers.json（答案、评分、解释与来源）、verification.json（计算与复核）、代码和题型快照。已有目录拒绝覆盖。输入哈希保存在验证记录中；原输入需按 manifest 保留，当前演示输入全部已在 docs/assets/ 版本控制中。

这是新的题型级批量试跑，不是旧题完整 M0–M6 重跑，也不自动进入目录。现有 42 道配额及 38 道待修处置保持不变；本轮没有新增 12 道 benchmark 题。短答案的几何子任务可能比原多部分题更窄，不能声称完整替代原评分。

## 输入、答案和评分

- 数值：输出一个有限数值及指定单位；当前两类为 Å、四位小数、half-up 舍入、绝对容差 0.00005 Å。明确容差，不做浮点逐字相等。几何代码仍需测试。
- 选项：可容纳数值、结构或修改方案。未来模板需校验唯一性或多选答案集合、干扰项和标签映射；不是本轮已实现能力。
- 结构：需要有效性、目标与约束评价器，通常允许多个解；当前未开放。

学生包没有参考答案、解题解释或审核证据。必要条件和实际几何输入必须给学生。审核侧保存解释、来源和数值验证。本轮网页公开显示答案是为了开发审阅；这些公开例子不能再作为保密测试集。

## 不再逐题反复交给模型裁决

每个新模板或模板修订先集中检查：科学意义、几何必要性、推理尺度、适用条件、结论是否过强、可执行评分。模板稳定后同代码检查所有实例：解析、单位声明、数值、输入哈希、运行结果与错误。

抽样按模板、来源和边界情况分层；新来源、改解析器、改模板、模型假设变化或异常结果必须增加检查。具体抽样比例尚未确定，不将会议例子当固定配额。程序无法证明来源语义、实验适用性或假设正确；不能因为数值通过而免除这部分检查。

## 三类能力采用不同细节

- 感知：真实结构 → 固定模板 → 确定性答案与验证。
- 推断：结构和必要条件 → 物理模型或论文支持的关系 → 简短数值/选项；原文证据用于审核，不默认泄漏给被测模型。
- 设计选择：真实有验证的 S1→S2 案例，或按规则筛出的结构对，加上目标性质证据 → 选择结构或修改方案 → 验证候选、限制和选项。不能把结构不同等同于性能改善。
- 开放设计：额外依赖结构评价器。当前 M3 仍拒绝 design；设计选择将单独实现准入，不能直接删掉保护后声称已支持。

## 可见入口与下一步

网站 templates.html 显示题型状态、实际输入输出、浏览器复算、Python 交叉核验及代码。builder.html 用三步组织工作，保留七模块实现查看器。

下一步：优先把 32 道小修按题型归组，先改模板；再迁移局部距离/角度的短答案批量接口；为推断选择、设计选择各找一个证据充分的具体模板。不要把已有纯数值感知换标签当设计。


## 四选一规则
选择题统一为四项 A/B/C/D、唯一正确；感知用数值/空间关系，推断用性质/范围/结论，设计选择用四个结构或明确修改方案。详见 [ANSWER_FORMATS.md](ANSWER_FORMATS.md)。自动选项构造与四项科学验证尚未实现；现有12个数值试跑不变。


## 两类数值题的四选一适配器（2026-09-23）
`choice_engine.py` 读取已验证的数值试跑，复核输入哈希并重算答案，再生成三项错误计算、排除舍入/容差重复、按记录种子打乱标签、输出独立学生包与审核包。凑不齐则记录失败，不生成任意数值。此入口对应 M4–M6 的专用试跑，尚未自动接入旧 pipeline 的通用构题路径，也不自动改变题库准入。

```text
python template_engine.py --manifest templates/pilot-manifest.json --out runs/numeric-new
python choice_engine.py --source runs/numeric-new --out runs/choice-new --seed geobench-choice-v1
python tools/export_choice_workbench.py --run runs/choice-new --public-development-examples
```

只允许已公开 pilot 材料通过此发布器。新 run 保存输入学生包、源报告与 manifest 副本、两个执行脚本、答案/错误机制/映射及验证报告。快照供审计；完整复现应在匹配版本的仓库根目录使用版本化 docs/assets 与上述命令，不把快照目录当作独立安装包。12例是原有题的格式试跑，不新增题数，不代替人工科学审核。网页 templates.html 可切换实例并展开记录。标签评分接受大小写和首尾空白，拒绝长文本。位置分布和干扰项质量需在更大批次检查；种子排序并不保证小批次均匀。


## 可复用题型族接口（2026-09-24）
`task_families/` 把共用机制放在 `kit.py`（严格 XYZ 解析、距离/键角/二面角两种实现、成键规则、舍入、干扰项选择、四项校验、单字母评分、捷径诊断），每个题型族只写科学部分：问什么、正确答案怎么算、哪些错误机制产生干扰项。`family_engine.py` 按 `templates/family-manifest.json` 分派族函数，不按题号选算法；输出学生包、数值作答学生包、审核包、阶段记录与代码快照，已有目录拒绝覆盖。

| 能力 | 族 | 实例（真实输入） |
|---|---|---|
| 感知 | named_bond_angle | β-CD 桥氧、WP6 环内角、DM-β-CD 甲醚（SAMPL9） |
| 感知 | backbone_torsion | 1CRN Gly20 φ、1UBQ Val26 ψ、6LYZ Thr43 φ |
| 推断 | force_path_derivative | QM7-X 7001/7002/7035（路径方向在实例间变化） |
| 推断 | kinematic_extinction | NaCl、金刚石、SALEM-2、MOF-5（COD） |
| 设计选择 | conformer_target_selection | QM7-X 7050/7206/7095/7032（7063 无唯一最优，记录失败） |
| 感知（选项 v0.2） | extent_choice_v2 | 原 12 份最大间距/回转半径输入 |

数值选项升序排列，正确值的秩在同一族批次内轮换；易排除的干扰项和“±”配对都计惩罚；分类选项把正确项放在批次轮换位置。凑不齐三个有依据的干扰项或唯一最优时记录失败。设计选择只用计算性质证据并逐项检查约束，旧 M3 对 design 的拒绝未改动。

```text
python family_engine.py --manifest templates/family-manifest.json --out runs/family-new --seed geobench-family-v1
python tools/export_family_workbench.py --run runs/family-new --public-development-examples
python tools/export_coverage.py
```

`templates/registry.json`（v0.2）是题型覆盖总表的唯一定义来源，`docs/data/task-coverage.json` 由它导出；旧 80 道候选与 50 个筛查族全部映射到其中一行（测试强制）。

## 独立检查器：题型级轻量验证（2026-09-24）
第五次会议要求“每种题型写一段确定性代码检查 input→output，代码正确即可检查该题型全部实例，模型只做抽查”。实现为 `checkers/`：
- **独立**：不导入 task_families、family_engine、template_engine、choice_engine 或 tools（测试以语法树检查强制）；只读取被测模型看到的学生包（题干、附件、选项）与答案键。
- **从题干读参数**：原子行号、二面角定义、路径方向、散射权重、设计目标都从题干文字中重新读出；读不出即失败，表示题目不能仅凭自身作答。
- **换公式重算**：键角用三边余弦定理（出题用向量点积）；二面角用法向量 acos 加三重积定号（出题用两种 atan2）；尺度量用 40 位 Decimal；受力投影逐原子 Decimal 求和；消光用独立 cos/sin 求和；设计题用自己的成键图、四配位中心手性和距离矩阵检查约束，按坐标（不按标签或编号）匹配数据集性质。
- **全部四项**：恰好一项等于重算值的舍入结果，其余在容差外；答案键字母与数值一致；学生包无答案键字段；输入与公开来源 SHA-256 一致（二面角片段须逐行出自原 PDB，受力与坐标须与资产一致）。
- **不做的事**：不判断科学意义、来源解读和适用条件，这些仍由模板审查与分层抽查负责。

```text
python verify_all.py --run runs/family-pilot-v01 --out runs/family-pilot-v01-independent-check.json
```
任何实例不一致时退出码为 1，`tools/export_family_workbench.py` 也会拒绝发布；通过的报告连同检查器代码写入 `docs/data/independent-check.json`。测试含手算例（正方形、类水分子键角、IUPAC −90° 二面角）与篡改例（改答案键、重复选项、改坐标、改 PDB 片段、删物理条件、换候选、泄漏编号、哈希不符），检查器必须全部拒绝。
