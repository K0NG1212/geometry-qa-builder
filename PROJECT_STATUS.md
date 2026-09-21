# 当前交接状态

更新：2026-09-21，执行助手 Claude Sonnet 5（Claude Code 会话，claude-sonnet-5）。任务：用户要求"继续"生成下一批，数量不设上限，由助手自行判断。本轮新增 10 道生物候选（bio-nm-v04-003/004/005 三个子运行），全部通过复用本项目已验证、已提交的真实结构（6LYZ、1CRN、1BNA）挖掘此前未问过的亚纳米局部几何特征（二硫键键长、α螺旋 Cα 间距、Watson-Crick 碱基对氢键），**未做任何新的网络检索**。生物 × 0.1–1 nm 由空格（0/10）补满到 10/10，与已完成的生物 × 1–10 nm 一起，生物域两格全部完成。

## 当前基线

- 本次提交前 HEAD：`8ded5f0`（"Add three H26DM-B-CD chemistry QA..."，上一轮已推送）；本次新增 10 道 QA 的提交见 Git 实际记录，本文件不是提交锁。
- 当前构题标准：PROTOTYPE.md 和 builder_modules/m0_scope/prototype-policy.json 的 v0.4，未变更。
- 目标 160，完整初筛候选 41（31+10），缺 119；正式可用计数 0。41 条均待人工审核。
- 31 个旧规划方向及 33 条历史记录不计入当前候选；不要重新放回主图充数。

## 已完成的当前题库

| 批次/本地 run | QA | 数量 |
|---|---|---:|
| prototype-v04-bcd-001 | CNP001 | 1 |
| chem-local-v04-002-r1 | CNP002、CNP003（其他历史记录不自动计入） | 2 |
| chem-local-v04-003 | CNP005、CNP006、CNI001 | 3 |
| q02-force-v04-001 | QNP001 | 1 |
| paper-hbond-v04-001-r1 | HBP001、HBP002、HBI001、HBI002 | 4 |
| bio-nm-v04-001 | BNP001–003、BNI001–002 | 5 |
| bio-nm-v04-002 | BNP004–006、BNI003–004 | 5 |
| bio-nm-v04-003 | BNP007–009、BNI005–006 | 5 |
| bio-nm-v04-004 | BNP010–011、BNI007–008 | 4 |
| bio-nm-v04-005 | BNP012 | 1 |
| materials-cell-v04-001 | MNP001–003、MNI001–003 | 6 |
| materials-cell-v04-002 | MNP004、MNP005、MNI004、MNI005 | 4 |

运行目录均在本仓库本地 runs/ 下且被 Git 忽略。题号归属和当前处置以 docs/data/catalog.json 为准；缺口查 docs/data/prototype-progress.json，审核入口为 docs/audit.html。

## 本轮：bio-nm-v04-003 / 004 / 005（生物 × 0.1–1 nm，从空格补满至 10/10）

这三个子运行是同一条思路的延伸：**不做新检索，只在已验证结构里挖掘此前未问过的亚纳米局部特征**。凡是把多个局部特征合并会让推理范围超过该格 [0.1,1) nm 上限的组合（例如同一蛋白质的全部二硫键一起问），题目都明确拆开或换用跨度更小的原子子集，并在 evidence/tasks 里写清原因，没有为了省事而超出尺度定义。

- **bio-nm-v04-003**（复用 6LYZ.pdb，与 bio-nm-v04-002 用的文件逐字节核对一致）：BNP007/BNP008 分别测溶菌酶两个真实二硫键（Cys6-Cys127、Cys30-Cys115）SG-SG 键长，与条目自带 SSBOND 记录独立核对一致；BNP009 测 α 螺旋（HELIX 记录，残基25-35）相邻/隔四残基 Cα 间距；BNI005 比较另两个二硫键（Cys64-Cys80 vs Cys76-Cys94，4 原子组合刚好在 1nm 边界内）的键长差异，推断化学合理性；BNI006 比较螺旋内两组隔四残基间距的规律性。
- **bio-nm-v04-004**（复用 1CRN.pdb，与 bio-nm-v04-001 用的文件逐字节核对一致）：BNP010 测 crambin 第三个二硫键（Cys16-Cys26）；BNI007 比较另两个二硫键（Cys3-Cys40 vs Cys4-Cys32）；BNP011 测 crambin 螺旋隔四残基间距（残基 9-13，避开条目自带记录里标注为畸变的 17/19 区域）；BNI008 是跨蛋白质推断——直接引用 bio-nm-v04-003 已通过的 BNP009 数值（6LYZ，6.248 Å）与 crambin 的新测值（6.065 Å）比较，两个互不相关蛋白质的螺旋隔四残基间距相差不到 3%，支持"规则 α 螺旋此间距是跨蛋白共有几何规律"的结论；不重新计算 BNP009。
- **bio-nm-v04-005**（复用 1BNA.pdb，与 bio-nm-v04-001 用的文件逐字节核对一致）：BNP012 测真实 Watson-Crick G(链A第2位)-C(链B第23位) 碱基对的三条氢键供体-受体距离（N1-N3、N2-O2、O6-N4，均落在经典 2.7–2.9 Å 范围），与条目自带 SEQRES 记录核对碱基身份，并推理 G-C（3 条氢键）比 A-T（2 条氢键）更耐热的教科书结论。恰好补满该格最后 1 个名额。
- 计算与复核：每个子运行都有独立的 `independent_checks.py`（Decimal 精度重算，并与条目自带 SSBOND/SEQRES 记录交叉核对），10 道全部通过；新增 tests/test_bio_geometry3.py、test_bio_geometry4.py、test_bio_geometry5.py（共 17 项单元测试，全部从已提交的 docs/assets/bio/*.pdb 读取，不依赖本地 runs/）。
- 报告：[bio-batch.html](docs/bio-batch.html) 已扩充第三批区块（合并展示三个子运行，因主题高度统一）；题目附件在 docs/assets/qa/；原始 PDB 复用既有 docs/assets/bio/{6LYZ,1CRN,1BNA}.pdb（未新增文件）；公开模块摘录在 docs/data/traces/；处置记录见 docs/data/qa-disposition.md。
- docs/audit.html "生物批次" 入口文字已更新为"两格已各补满 10/10"。

## 上一轮（已推送，供参考）：materials-cell-v04-002 / bio-nm-v04-002 / chem-local-v04-003 各批要点

- **materials-cell-v04-002**：MgO/CsCl 新 COD 结构，补满材料 × 0.1–1 nm。
- **bio-nm-v04-002**：6LYZ/1EHZ（本项目首个 RNA 结构）新检索，补满生物 × 1–10 nm。
- **chem-local-v04-003**：SAMPL9 的 H26DM-B-CD 新检索，补满化学 × 0.1–1 nm；同时修复了 tests/test_materials_batch2.py 误读本地被忽略的 runs/ 目录的可移植性问题，把计算脚本正式发布为 tools/recompute_materials_batch2.py。
- 详见 Git 历史提交 `8f9d138`、`7a5f96a`、`8ded5f0` 的完整说明。

## 实际执行的检查（本轮）

- `python -m unittest discover -s tests -v` 全部 96 项通过（82 旧 + 6 test_bio_geometry3 + 5 test_bio_geometry4 + 3 test_bio_geometry5）。
- `tools/export_prototype.py`/`export_admission_audit.py`/`export_modules.py` 均重跑成功。
- 本地起 HTTP 服务器用浏览器核对了 index.html 候选列表（41 道）、audit.html 16 格覆盖表（生物两格均 10/10）、trace.html 对新题（含 BNI008、BNP012）的 M0–M6 记录、bio-batch.html 新区块、以及全部新增静态资源（.xyz/输入文本）的 200 响应。
- 未做专家审核或模型难度试测。初筛数 41、人工待审 41、无已明确人工确认的题号（与上一份交接记录一致，用户此前提到"审核了几条"但未指定编号，未据此改状态）。

## 下一项工作

材料 × 0.1–1 nm、生物 × 0.1–1 nm、生物 × 1–10 nm、化学 × 0.1–1 nm 四格已补满。下一步按覆盖统计（docs/audit.html 16 格表）选缺口继续：量子域全部四格（各 9–10 缺口，全库最大空白，QNP001 之外无其他已用材料/方法可直接复用，需要新的计算化学数据源）、化学 1–1000 nm 三格（各 10 缺口，全新尺度需新材料）、材料 1–1000 nm 三格（各 10 缺口）、生物 10–1000 nm（10 缺口，空白）。"复用已验证结构挖掘未问过的局部特征"这条思路（本轮对生物域的做法）值得在其他领域尝试：比如材料域已用的 COD 结构里是否还有未问过的局部几何（键角、次近邻壳层等），化学域的 SAMPL9 host/guest 复合物是否有未测的局部基元，但要注意扩大到 1–1000 nm 尺度格时通常仍需全新材料（局部特征挖掘只能填同一尺度格内的空缺，不能跨尺度）。继续遵循：先确认来源、材料和验证器，再跑新批次；允许不足，不为凑齐设计题降低验证标准。用户已明确本轮批次数量不设固定上限，由助手依材料可得性和验证质量自行判断规模。

## 提交/远端同步/Pages 状态

- 提交前 `git fetch` 确认与 origin/main 一致（无分叉），工作树在开始前干净。
- 本次改动已提交并推送（见 Git 实际记录）；Pages 部署未在本会话验证（无法访问已部署的 GitHub Pages URL），仅本地起服务器验证过静态资源可达，上线情况需下一位助手或用户核实。

## 接手时哪些东西可获得

| 位置 | 用途与限制 |
|---|---|
| GitHub 仓库 | 代码、规则、公开题目、附件和公开 trace；可在新机器使用 |
| 本地 runs/<run-id>/ | 冻结 pipeline、packet、context、全部阶段结果、报告；只有这份才可恢复原运行 |
| 本地 inputs/ 及仓库外工作目录 | 部分原始下载和辅助脚本；不随 Git 同步，不应成为新机器的隐含依赖 |
| docs/data/traces/<QA-ID>.json | 脱敏公开摘录，有所省略，不能当成完整恢复包 |

同机接手从仓库根目录查看实际 run，再按 RUNBOOK 恢复。异机先检查缺失项：要继续原 run 需私有移交完整目录及它实际依赖的文件；仅参考已有题后生成新批次可重新获取公开来源并新建 run。不要公开上传全文或凭摘要补造历史。

## 每次交接更新模板

- 日期、执行助手、任务和所基于的提交：
- 本次新增/修改的题号与 run ID：
- 当前阶段及已保存输入输出位置：
- 来源、计算/评分方法及限制：
- 实际执行的检查与结果（未执行也说明）：
- 初筛数、人工待审数、已明确人工确认的题号：
- 未完成事项、原因、下一步：
- 提交/远端同步/Pages 状态（分别说明；可记录上一批提交或用 Git HEAD，避免自引用哈希）：
