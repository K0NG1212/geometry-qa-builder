# 当前交接状态

## 下一阶段交接（2026-09-24）

用户指出两个计算模板仅覆盖感知的一小部分，要求交接Claude Code推进更广题型。下一阶段顺序改为：盘点有依据的题型覆盖→复用既有代码建立可扩展接口→推进不同能力的代表模板与少量真实试跑→网站展示；已有选项捷径同时处理，但不再把整轮工作限制于两个计算器。任务书见 [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md)，入口CLAUDE.md已链接。此轮仅补交接文档，未新增题、未改变准入或审核状态，未实施上述下一阶段任务。实现基线d726700；下方2026-09-23的“下一步”已由本条更新。

## 最新：两类数值题四选一试跑（2026-09-23）

- 新增 choice_engine.py，独立于原数值计算器。按实际结构生成正确答案及错误机制干扰项，排除显示重复/容差重叠，确定性打乱并保存映射；不凑任意错误数。评分只接受单字母（忽略大小写与首尾空白）。
- runs/choice-pilot-v02 从原 runs/template-pilot-v01 的12份输入生成，12/12程序检查通过。v01保留为开发记录，v02新增难度诊断；旧数值运行未改。学生包与审核包分离，源记录/代码/材料哈希可追溯。
- 新增 tools/export_choice_workbench.py，仅允许既有公开pilot，核对快照并复算选项。公开 docs/data/choice-workbench.json、templates.html#choice-lab；12实例切换，48个选项评分及手机布局已检查。原数值复算区仍可用。
- 162项程序测试通过（新增6项），后续补充大小排名诊断仅需复跑选项相关测试。答案位置 A3/B5/C3/D1。注意：最大间距9题中5题正确值最大，回转半径3题中2题最小；两种简单规则合计7/12，尚未验证难度，不应直接入正式测试集。
- 全部 pending 人工审核；新增题库计数0，当前42 active不变。推断/设计选择未实现，旧通用M4路径未自动接入本适配器。
- 下一步：先抽查两类干扰项的合理性并降低大小排序捷径，再迁移其他计算题；设计题仍需四结构与性质证据。发布状态按最终提交/Pages核查。

以下为历史记录：

## 最新补充：四选一答案规范
用户明确选择题为四项唯一正确，设计题可从四个结构选一个。规则写入 ANSWER_FORMATS.md、templates/answer-policy.json 及 M3/M4/M5 提示词，并在 templates.html 展示。当前仅规则已定义；没有生成四选一题，没有更改12个数值试跑或题库计数。


## 第五次会议实施：题型级批量试跑（2026-09-22）

- 方法展示改为定义→构造→验证；M0–M6 保留作为底层实现，旧快照不改。
- 新增 METHODOLOGY.md、templates/registry.json、template_engine.py；最大间距、等权回转半径两个可复用模板在12份既有公开 XYZ 上实际运行，12/12数值核验通过。0次模型调用指批量构造计算阶段，不指整个项目成本。
- 本地 runs/template-pilot-v01：manifest、学生包、私有答案、验证报告、代码及注册表快照。公开演示页 templates.html 可查看输入输出并在浏览器复算。代码和输入哈希保存。
- 本轮不是新增12道正式候选，未完整重跑旧题M0–M6，题库仍42 active/38待修，全部保留原审核状态。
- 六类题型目录中：2已实现本轮接口，1类局部距离/角度已有旧实现待迁移，推断选择与设计选择待建立实证模板，开放结构生成缺评价器。当前M3设计门槛没有假装解除。
- 下一步按题型处理32道小修，迁移局部计算器，并建立首个论文支持的设计选择模板。本轮156项程序测试通过；网页已检查12次浏览器复算、正确/错误答案评分、学生包分离、Builder入口及手机布局。部署状态以最终提交为准。

---


## 最新接手复查：2026-09-22（以下原会话记录作为历史保留）

- 基线 ae7314c；完成 80 道题干、输入说明、答案、评分、尺度的专项审读，非全文重新查证、数值全量重算或专家审核。
- 结果：42 保留待人工审核、32 小修后复查、6 重构（QNI004–009）。80 道和冻结运行均保留；38 道移到 rework，当前计入配额 42/160，缺 118。原始审核状态不变，不擅自批准。
- 小修是工作量建议，不代表已修改完成。优先处理比值方向、尺度、评分边界和缺失参考输入；需要补证据的仍须返回 M1/M2。
- 公开结果 docs/screening.html，逐题 JSON/Markdown 为 docs/data/focused-screening.*；catalog.focusedScreening 为本次处置说明，原 snapshot 未改。
- Builder M3/M5 0.4.1：强制真实运行 geometry_audit；必填几何输入、移除后的剩余作答、依赖评分、尺度、结论边界、任务族，拒绝矛盾通过。程序不自动验证语义。
- 原来源分布 76 数据/4 论文，原能力 44 感知/36 推断/0 设计。批量扩展仍需改善分布，不能靠改变标签填配额。
- 本轮 149 项程序测试通过；网页本地检查覆盖 80 条清单、42/32/6 筛选、42 待审及 71 历史记录；最终发布以 Git 提交和 Pages 状态为准。后续修改题目应新建 run，不回填原运行。

---


更新：2026-09-22，执行助手 Claude Sonnet 5（Claude Code 会话，claude-sonnet-5）。本文件是这次会话八轮工作的**合并总结**（此前分批提交逐步更新，现整合为一份连贯记录，方便下一位助手/智能体接手）。

**用户指示**：读取 CLAUDE.md/PROJECT_STATUS.md 核对状态后，按现有 Builder 继续生成候选题；数量不设 6 道上限，由助手自行判断规模；用户随后六次说"继续"/"再做一批吧，这次多做点，不用在意运行时间"/"继续做下一批,量子1-10nm"/"继续下一批,材料1-10nm"/"继续下一批,化学1-10nm"。

**本次会话总产出**：新增 **61 道**候选题（19→80，占目标 160 的比例从 12% 提升到 50%），补满 **8 个尺度格**（材料×0.1–1nm、化学×0.1–1nm、生物×0.1–1nm、生物×1–10nm、量子×0.1–1nm、量子×1–10nm、材料×1–10nm、化学×1–10nm），全部走完整 M0–M6、双方法独立复核、pending_human_audit。**四个领域的两个"起步"尺度格（0.1–1nm 与 1–10nm）现已全部补满**。前 7 批已推送到 origin/main；第 8 批（chem-nm，化学 1–10nm）为本次更新新增，见下方提交表最后一行：

| 提交 | 内容 | 新增题数 |
|---|---|---:|
| `8f9d138` | materials-cell-v04-002（MgO/CsCl 新 COD 结构） | 4 |
| `7a5f96a` | bio-nm-v04-002（6LYZ/1EHZ 新 PDB 结构，本项目首个 RNA） | 5 |
| `8ded5f0` | chem-local-v04-003（SAMPL9 H26DM-B-CD 新结构）+ 修复测试可移植性 bug | 3 |
| `2e35100` | bio-nm-v04-003/004/005（复用已验证结构，挖掘亚纳米局部几何，零新检索） | 10 |
| `58b54cd`→`5514a49` | q02-force-v04-002（QM7-X 新增 5 分子，量子×0.1–1nm 补满） | 9 |
| `387915b`→`44a01e5` | quantum-nm-v04-001/002（OE62 数据集新引入，量子×1–10nm 补满） | 10 |
| `f309aab`→`5ca3114` | materials-nm-v04-001（COD 大晶胞 MOF 新引入，材料×1–10nm 补满） | 10 |
| `538e775` | chem-nm-v04-001（PDB 万古霉素二聚体新引入，化学×1–10nm 补满） | 10 |

## 当前基线

- HEAD：`538e775`（chem-nm-v04-001，已推送），父提交 `5ca3114`。
- 构题标准：PROTOTYPE.md 和 builder_modules/m0_scope/prototype-policy.json 的 v0.4，本会话未变更任何 Builder 代码逻辑（仅新增复算/发布脚本，属于既定模式的延伸）。全部题目走 evidence_review（全局尺度扫描、最近接触、回转半径均非 xyz_distance/xyz_angle 注册验证器类型）。
- 目标 160，完整初筛候选 **80**，缺 80（恰好过半）；正式可用计数仍为 0（无专家审核）。80 条均 pending_human_audit。
- 31 个旧规划方向及 33 条历史记录不计入当前候选；本会话未触碰这些历史记录。

## 16 格覆盖现状（docs/audit.html 实时数据，docs/data/prototype-progress.json 来源）

| 领域 | 0.1–1 nm | 1–10 nm | 10–100 nm | 100–1000 nm |
|---|---:|---:|---:|---:|
| 量子/电子结构 | **10/10** ✅ | **10/10** ✅ | 0/10 | 0/10 |
| 化学 | **10/10** ✅ | **10/10** ✅ | 0/10 | 0/10 |
| 材料 | **10/10** ✅ | **10/10** ✅ | 0/10 | 0/10 |
| 生物 | **10/10** ✅ | **10/10** ✅ | 0/10 | 0/10 |

本会话前状态：材料 6/10、化学 7/10、生物 0.1–1nm 0/10、生物 1–10nm 5/10、量子 0.1–1nm 1/10、量子 1–10nm 0/10、材料 1–10nm 0/10、化学 1–10nm 0/10。八格全部由本会话补满。**四个领域 × 两个起步尺度格（0.1–1nm、1–10nm）共 8 格全部见底**，剩余 80 个缺口全部集中在 10–100nm 与 100–1000nm 这两个更大的尺度格（每领域各 2 格，共 8 格）。量子/材料/化学三次突破 1nm 起步格都遵循同一模式："引入专门覆盖更大尺度的新数据源"+"用全局尺度/晶胞级/整分子级方法代替局部键角方法"，三次成功验证了这条路径的可靠性；生物域 1–10nm 格本会话开始时已有 5/10（蛋白质/DNA 结构，此前批次留下），本会话 bio-nm-v04-002 用同一批已用 PDB 结构补满剩余 5 道，未额外引入新数据源。

## 已完成的当前题库（完整清单）

| 批次/本地 run | QA | 数量 |
|---|---|---:|
| prototype-v04-bcd-001 | CNP001 | 1 |
| chem-local-v04-002-r1 | CNP002、CNP003 | 2 |
| **chem-local-v04-003**（本会话） | CNP005、CNP006、CNI001 | 3 |
| q02-force-v04-001 | QNP001 | 1 |
| **q02-force-v04-002**（本会话） | QNP002–006、QNI001–004 | 9 |
| **quantum-nm-v04-001**（本会话） | QNP007–011、QNI005–008 | 9 |
| **quantum-nm-v04-002**（本会话） | QNI009 | 1 |
| **materials-nm-v04-001**（本会话） | MNP006–010、MNI006–010 | 10 |
| **chem-nm-v04-001**（本会话） | CNP007–011、CNI002–006 | 10 |
| paper-hbond-v04-001-r1 | HBP001、HBP002、HBI001、HBI002 | 4 |
| bio-nm-v04-001 | BNP001–003、BNI001–002 | 5 |
| **bio-nm-v04-002**（本会话） | BNP004–006、BNI003–004 | 5 |
| **bio-nm-v04-003**（本会话） | BNP007–009、BNI005–006 | 5 |
| **bio-nm-v04-004**（本会话） | BNP010–011、BNI007–008 | 4 |
| **bio-nm-v04-005**（本会话） | BNP012 | 1 |
| materials-cell-v04-001 | MNP001–003、MNI001–003 | 6 |
| **materials-cell-v04-002**（本会话） | MNP004、MNP005、MNI004、MNI005 | 4 |

运行目录均在本仓库本地 runs/ 下且被 Git 忽略（新机器不存在，属预期）。题号归属和当前处置以 docs/data/catalog.json 为准；缺口查 docs/data/prototype-progress.json；审核入口 docs/audit.html；处置记录 docs/data/qa-disposition.md。

## 四个子批次详情

### 1. materials-cell-v04-002 — 材料 × 0.1–1 nm（6/10 → 10/10）

- **来源**：COD 官方结构 1000053（MgO periclase，Sasaki/Fujino/Takeuchi 1979）、9008789（CsCl，Wyckoff 1963，与项目已用卤化钠同源卷）。真实新检索（curl 直连 crystallography.net）。
- **内容**：MgO 岩盐型近邻壳层（MNP004）、CsCl 原生纯净立方 8 配位新几何类型（MNP005）、MgO 晶面间距/Bragg 角（MNI004）、CsCl 结构因子化学对比/体心立方消光定则（MNI005，区分"晶格禁戒"vs"化学对比禁戒"）。
- **复核**：Decimal 闭式距离、余弦定理反算夹角、Bragg 反代恢复波长、闭式结构因子公式，四道全部通过。
- **产物**：runs/materials-cell-v04-002/、docs/materials-batch.html 新区块、docs/data/materials-batch-v2-*.json、docs/assets/materials/{1000053,9008789}.cif、tests/test_materials_batch2.py。
- **已知缺口**：曾尝试找 GaAs 闪锌矿、单质铜补充覆盖，会话内未定位到干净可用的 COD 记录，如实记录在 sources.json，留给后续。

### 2. bio-nm-v04-002 — 生物 × 1–10 nm（5/10 → 10/10）

- **来源**：RCSB PDB 6LYZ（鸡蛋清溶菌酶，Diamond 1974 经典结构）、1EHZ（酵母苯丙氨酸 tRNA，Shi & Moore 2000，**本项目首个 RNA 结构**）。真实新检索。
- **内容**：溶菌酶端距/最大尺寸/催化裂隙 Glu35–Asp52（身份由条目自带 HELIX 与立体化学记录独立确认，BNP004）；tRNA 骨架路径长度是端到端直线距离的约 24 倍，L 形折叠直接证据（BNP005）；反密码子三联体局部构象 134.53°，非完全共线，身份核对 SEQRES 为 OMG-A-A（BNP006）；溶菌酶与已通过 1UBQ/1CRN 三者回转半径比较，复用旧数值未重算（BNI003）；tRNA 虚拟 FRET 探针量程不匹配推断，r≈7.23nm 远超 R0=3.5nm，效率降到约 0.0127（BNI004）。
- **复核**：全扫描交叉验证、pairwise-distance 恒等式复核 Rg、atan2 交叉验证夹角、Decimal 精度复核 FRET，五道全部通过。
- **产物**：runs/bio-nm-v04-002/、docs/bio-batch.html 第二批区块、docs/data/bio-batch-v2-*.json、docs/assets/bio/{6LYZ,1EHZ}.pdb、tools/recompute_bio_batch2.py、tests/test_bio_geometry2.py。

### 3. chem-local-v04-003 — 化学 × 0.1–1 nm（7/10 → 10/10）

- **来源**：SAMPL9 官方仓库 host_guest/bCD/host_files/H26DM-B-CD.pdb（甲基化环糊精），与 CNP001（B-CD）同目录同生成方式。此前只被归档题 CNM003/CNM004 用过，未进入任何当前候选；本批不复用其旧内容，重新走完整 M0–M6。
- **内容**：桥连糖苷氧 C4-O3-C37 键角（CNP005，116.0251189°，与 CNP001 未甲基化数值差异仅约 4×10⁻⁸ 度）；甲基醚局部键角+两个键长，未甲基化结构中不存在的新局部基元（CNP006）；推断远端 2,6-位甲基化是否扰动糖苷环连接几何——直接引用 CNP001 数值比较，不重算（CNI001）。
- **复核**：acos 与 atan2 公式独立复核角度，Decimal 精度复核差值，三道全部通过。
- **重要修复**：发现 tests/test_materials_batch2.py 此前误从本地 runs/materials-cell-v04-002/ 读取材料和脚本（Git 忽略目录，新机器不存在，会导致该测试在新 clone 上必然失败）。已修复：计算脚本正式发布为 **tools/recompute_materials_batch2.py**（之前是本轮次批次遗漏，只存在于本地 run 未提交），测试改为从已提交的 docs/assets/materials/ 读取。
- **产物**：runs/chem-local-v04-003/、docs/chem-local-batch.html 新区块、docs/assets/qa/{CNP005,CNP006,CNI001}-input.txt、复用既有 docs/assets/qa/DMBCD.xyz（与归档题字节级一致）、tests/test_chem_geometry3.py。

### 4. bio-nm-v04-003/004/005 — 生物 × 0.1–1 nm（0/10 → 10/10）

**关键差异**：这三个子批次**没有做任何新的网络检索**，而是复用本会话/前几轮已验证并已提交到 Git 的三份真实结构（6LYZ.pdb、1CRN.pdb、1BNA.pdb，均逐字节 diff 核对一致），转而测量这些结构里此前从未被问过的**亚纳米局部特征**：

- **bio-nm-v04-003**（6LYZ）：两个真实二硫键 SG-SG 键长（Cys6-Cys127、Cys30-Cys115，与条目自带 SSBOND 记录独立核对，BNP007/BNP008）；α螺旋（HELIX 记录，残基25-35）相邻/隔四残基 Cα 间距（BNP009）；另两个二硫键（Cys64-Cys80 vs Cys76-Cys94）化学一致性比较，4 原子组合刚好卡在 1nm 边界内（BNI005）；螺旋内两组隔四残基间距规律性推断（BNI006）。
- **bio-nm-v04-004**（1CRN，crambin）：第三个二硫键 Cys16-Cys26（BNP010）；另两个二硫键 Cys3-Cys40 vs Cys4-Cys32 比较（BNI007）；螺旋隔四残基间距，刻意选残基 9-13 避开条目自带记录标注为畸变的 17/19 区域（BNP011）；**跨蛋白质推断**——直接引用 bio-nm-v04-003 已通过的 BNP009 数值（6LYZ，6.248 Å），与 crambin 新测值（6.065 Å）比较，两个互不相关蛋白质螺旋间距相差不到 3%，不重算 BNP009（BNI008）。
- **bio-nm-v04-005**（1BNA）：真实 Watson-Crick G(链A第2位)-C(链B第23位) 碱基对三条氢键供体-受体距离（N1-N3、N2-O2、O6-N4，均落在经典 2.7–2.9 Å 范围），身份核对条目自带 SEQRES 记录，推理 G-C（3 氢键）比 A-T（2 氢键）更耐热（BNP012）。恰好补满该格最后 1 个名额。
- **方法论要点**：凡是把多个局部特征合并会让推理范围超过该格 [0.1,1) nm 上限的组合（例如同一蛋白质全部二硫键一起问），题目都明确拆开或换用跨度更小的原子子集，并在 evidence/tasks 记录里写清原因（不是随意省略，是算过 span 超界才排除）。
- **复核**：每个子运行都有独立的 `independent_checks.py`（Decimal 精度重算，交叉核对条目自带 SSBOND/SEQRES 记录），10 道全部通过。
- **产物**：runs/bio-nm-v04-{003,004,005}/、docs/bio-batch.html 第三批区块（合并展示三个子运行）、docs/assets/qa/ 下 10 组附件、tests/test_bio_geometry{3,4,5}.py（共 14 项新测试）。未新增 docs/assets/bio/ 文件（完全复用已有的）。

### 5. q02-force-v04-002 — 量子 × 0.1–1 nm（1/10 → 10/10）

- **来源**：QM7-X 官方 Zenodo 记录 4288677 的同一分片 **8000.xz**（md5 `c893ae88b8f5c32541c3f024fc1daa45`，与 QNP001 使用的文件逐字节一致；本会话本地未发现缓存，重新下载并核对校验值一致），另取 5 个与 QNP001（分子7001）不同的分子：7002、7035、7040、7070、7122（用标准共价半径距离启发式扫描确认各分子含硫/氯/氮等不同官能团类别，作为选取依据，不写入题干）。
- **内容**（5 感知 + 4 推断，设计=0）：QNP004（7002，N-N 间距 1.1872 Å）、QNP002（7035，S-O 间距 1.4616 Å）、QNP005（7040，O-S-O 夹角 121.96°）、QNP003（7070，C-Cl 间距 1.7372 Å）、QNP006（7122，C-N 间距 1.4013 Å）；QNI001/QNI002（7002/7035，复用 QNP001 的 force_projection.py 方法，S 分别为 -0.4353 eV / -5.5319 eV，均反对形变）、QNI003（7040，新设计：比较同一分子两个独立位移 d1 与 d2 的力投影，S_d1=-11.8341 eV 与 S_d2=-5.0423 eV，|S_d1|>|S_d2|，不对物理可能性下结论）、QNI004（7070，新设计：由官方 vDIP 三分量计算偶极矩大小并比较 opt→d1 的带符号变化，-0.1049 e·Å，减小；用官方标量 DIP 场做内部一致性核查）。
- **方法升级**：5 道感知题首次改用 schema 已注册的**通用 xyz_distance/xyz_angle 数值验证器**（construction 阶段 answer_text=null，由可信 Python 代码从坐标直接计算参考答案），比 QNP001 用的 evidence_review 路由更严格；4 道推断题仍走 evidence_review + 补充计算器。M4 提示词明确禁止"仅凭原子间距推断成键/官能团"，因此所有感知题题干只描述"测得距离最短的某元素原子"，不使用"键""磺酰""磺酰胺"等化学命名（这些描述只留在内部 evidence 记录，作为选取原子对/三元组的依据说明）。
- **复核**：`runs/q02-force-v04-002/independent_checks.py` 重新用 h5py 直接解析 8000.hdf5（不导入本批主计算脚本），角度改用 atan2 公式（构造阶段用 acos），力投影和偶极矢量幅值全部改用 Decimal 精度；9/9 通过，且与通用验证器的自动计算结果逐位一致。
- **产物**：runs/q02-force-v04-002/（含 build_bundle.py/author_*.py/independent_checks.py/publish_assets_and_catalog.py 五个作者脚本）、新页面 docs/quantum-batch.html、docs/assets/qa/ 下 9 道题共 14 个 xyz 附件 + 9 个 input.txt、docs/data/traces/{QNP002,QNP003,QNP004,QNP005,QNP006,QNI001,QNI002,QNI003,QNI004}.json、tests/test_quantum_geometry.py（10 项新测试，全部从已提交的 docs/assets/qa/ 读取，不依赖 runs/）。

### 6. quantum-nm-v04-001/002 — 量子 × 1–10 nm（0/10 → 10/10）

- **背景**：这是本会话唯一需要**引入全新数据源**才能填补的尺度格。量子域此前只用过 QM7-X（单分子天然落在 0.1–1nm），无法直接扩展到 1–10nm。研究后选定 **OE62** 数据集（Stuke, Kunkel, Golze, Todorović, Margraf, Reuter, Rinke and Oberhofer, *Scientific Data* 7, 58 (2020), DOI 10.1038/s41597-020-0385-y）：从剑桥结构数据库（CSD）真实晶体中抽取的 61,489 个大分子，PBE+vdW 几何弛豫，PBE/PBE0/G0W0@PBE0 三级电子结构理论轨道能级，TUM mediaTUM DOI 10.14459/2019mp1507656 发布，CC BY-SA 4.0 许可。这套数据集论文摘要明确说明其设计目的就是**超出 QM9/QM7-X 的小分子尺度**。
- **取得方式**：mediaTUM 网页本身访问受限（"Access Denied"），改用其官方 FTP 端点（`ftp://m1507656:m1507656@dataserv.ub.tum.de:21/`）下载 df_62k.json（387MB）与 df_5k.json（GW5000 子集，51MB），两份文件的 SHA512 均与数据集自带的 SHA512sums 逐字节核对一致。从全部 62k 分子中按自身最大原子间距筛出 27,572 个落在 [1,10) nm 的分子，选取 10 个（跨度约 1.00–1.65 nm，元素含 Cl/Si/F/S/P，3 个另有 GW5000 数据）。
- **内容**（5 感知 + 5 推断，设计=0）：**全局尺度**族 QNP007/008/009（MAJHUB/JIMHOC/KEGPOC，穷举扫描全分子所有原子对找最大间距及取得该间距的两行，复用生物域 BNP001 已验证的方法族，要求真正搜索而非读出预给定原子对）；**回转半径**族 QNP010/011（KEWGID/PEKZAG，复用生物域 BNP002 完全相同的 Rg 公式）；**能隙**族 QNI005（GALPAL，单一 PBE 层级 HOMO/LUMO 读出）、QNI006/QNI009（MEHLOA/JIMHOC，同分子 PBE vs PBE0 两级比较）、QNI007（MAJHUB，同分子 PBE0 vs GW 两级比较）、QNI008（EZUTAU vs ZOGVEW 跨分子比较——原子数更多、尺度更大的 ZOGVEW 能隙反而更小，是一个具体可核查的反例，用于说明两点比较不能确立尺寸-能隙因果关系，不是套话式免责声明）。QNI009 是第二次续跑（quantum-nm-v04-002），复用 QNP008 已验证的 JIMHOC 几何补满第 10 个名额。
- **方法说明**：全部 10 道走 evidence_review（全局尺度扫描、回转半径、能隙提取/比较均非 schema 已注册的 xyz_distance/xyz_angle 验证器类型，与上一批部分题目可用通用验证器不同）。HOMO=占据列表升序最后一个值、LUMO=非占据列表升序第一个值，这一约定逐字引自 OE62 论文 Table 2 官方字段说明，不是本项目自行假设。回转半径任务的推理尺度用分子自身 Dmax（全部原子参与），不用更小的 Rg 数值本身，与上一批 QNI004 偶极矩任务的尺度约定一致。
- **复核**：`runs/quantum-nm-v04-001/independent_checks.py` 与 `runs/quantum-nm-v04-002/independent_checks.py` 用 pandas 独立重新读取原始 df_62k.json/df_5k.json（不导入本批主计算脚本 compute_oe62_batch.py），全局尺度/回转半径改用 Decimal 精度的穷举扫描独立实现，能隙改用独立的列表索引重新提取；10/10 全部通过。
- **产物**：runs/quantum-nm-v04-001/、runs/quantum-nm-v04-002/（各含 build_bundle.py/author_*.py/independent_checks.py/publish_assets_and_catalog.py 系列作者脚本）、新页面 docs/quantum-nm-batch.html、docs/assets/qa/ 下 10 道题共 12 个 xyz 附件 + 10 个 input.txt、docs/data/traces/{QNP007,QNP008,QNP009,QNP010,QNP011,QNI005,QNI006,QNI007,QNI008,QNI009}.json、tests/test_quantum_nm_geometry.py（12 项新测试，全部从已提交的 docs/assets/qa/ 读取，不依赖 runs/）。
- **未提交内容**：df_62k.json（387MB）与 df_5k.json（51MB）留在本机 runs/quantum-nm-v04-001/materials/，gitignored，不随 Git 同步；异机接手需按 sources.json 记录的 FTP 端点重新下载并核对 SHA512。

### 7. materials-nm-v04-001 — 材料 × 1–10 nm（0/10 → 10/10）

- **背景**：已用 COD 结构（Si、金刚石、NaCl、MgO、CsCl）晶胞全部远小于 1nm，无法直接扩展。研究后选定两个真实金属有机框架（MOF）晶体，其自身常规立方晶胞就落在 1–10nm：**ZIF-8**（COD 4118891，a=1.68303 nm，体心立方 I-43m，48 个对称操作；Karagiaridi et al., *J. Am. Chem. Soc.* 134, 18790 (2012)）与 **MOF-5**（COD 1516287，a=2.58247 nm，面心立方 Fm-3m，192 个对称操作，无无序；Lock et al., *J. Phys. Chem. C* 114, 16181 (2010)）。两条目均由 COD 贡献者置于公有领域，直接 curl 下载。
- **对称展开方法复用**：直接 import 已审核通过的 `tools/recompute_materials_batch2.py` 的 `read_cubic_cif`（用于 materials-cell-v04-002 的 MgO/CsCl），未修改该文件；展开后晶胞组成（ZIF-8: Zn12 C72 H72 N48；MOF-5: Zn32 O104 C192 H96）与 COD 官方 API 自带 cellformula 字段完全一致，独立确认展开正确。ZIF-8 的 CIF 用两列 `_space_group_symop_id`+`_space_group_symop_operation_xyz` 格式（该函数原本只认单列格式），因此写了一层预处理归一化，不改动共享工具本身。
- **无序处理**：ZIF-8 原始 CIF 记录一对连接体碳/氢（C2A/H2A）为 37% 占位的次要位点，本批工作坐标只用 63% 占位的主要位点（C2/H2）或完全有序原子（Zn1/N1/C1/H1），已在 bundle 证据中明确披露，不是隐藏处理。MOF-5 无任何无序。
- **内容**（5 感知 + 5 推断，设计=0）：**全局尺度**族 MNP006/007（ZIF-8/MOF-5 Zn 亚晶格穷举扫描）、MNP010（MOF-5 全部原子穷举扫描，与 MNP007 对照），复用生物/量子域已验证的全局尺度方法族，首次推广到周期性材料对象；**晶面间距**族 MNP008/009（ZIF-8 d(110)、MOF-5 d(111)），复用材料×0.1–1nm 已验证的立方晶面公式（MNP003），因晶胞大一个数量级使低阶反射间距本身落入 1–10nm；**布拉格角**族 MNI006/007，复用 MNI001/MNI004 方法族；**结构因子消光**族 MNI008（ZIF-8 体心 h+k+l=even 定则）/MNI009（MOF-5 面心全同奇偶定则），复用 MNI002/MNI005 方法族，在真实大晶胞骨架上验证；**比较**题 MNI010，引用 MNI008/MNI009 已算出的结果（不重算），推理出决定选择定则的是晶格中心化类型而非晶胞尺寸，并明确两个实例的结论边界（不是套话式免责声明——两个结构确实呈现出不同定则，用真实计算结果驱动论证）。
- **复核**：`runs/materials-nm-v04-001/independent_checks.py` 从零重写 CIF 对称展开（不导入 tools/recompute_materials_batch2.py，用 Decimal 精度 + 不同的字典去重算法），独立重新解析两份原始 CIF；10/10 全部通过。过程中发现并修复一处 Decimal 陷阱：`Decimal('-0.25') % 1` 不像 float/int 那样自动包裹到 [0,1)（返回 -0.25 而非 0.75），已显式补加包裹逻辑。
- **产物**：runs/materials-nm-v04-001/（含 build_bundle.py/compute_materials_nm.py/author_*.py/independent_checks.py/publish_assets_and_catalog.py 系列作者脚本）、新页面 docs/materials-nm-batch.html、docs/assets/qa/ 下 10 道题共 11 个 xyz 附件 + 10 个 input.txt、docs/data/traces/{MNP006,MNP007,MNP008,MNP009,MNP010,MNI006,MNI007,MNI008,MNI009,MNI010}.json、tests/test_materials_nm_geometry.py（12 项新测试，全部从已提交的 docs/assets/qa/ 读取，不依赖 runs/）。
- **未提交内容**：原始 CIF 文件（4118891.cif、1516287.cif，各约 11KB，公有领域）留在本机 runs/materials-nm-v04-001/materials/，gitignored；异机接手可直接从 crystallography.net 按 COD ID 重新下载，无需任何特殊权限。

### 8. chem-nm-v04-001 — 化学 × 1–10 nm（0/10 → 10/10，四领域最后一个起步格）

- **背景**：已用 SAMPL9 host/guest 结构（B-CD、WP6、H26DM-B-CD）均在 0.1–1.7nm 量级，其局部特征挖掘方法已在化学×0.1–1nm 格用尽。研究后选定 **PDB 1AA5**（万古霉素不对称二聚体，0.89 Å 超高分辨率；Loll, Bevivino, Korty and Axelsen, *J. Am. Chem. Soc.* 119, 1516 (1997)）：单个万古霉素分子已达 ~1.96nm，二聚体 ~2.87nm，天然落在 1–10nm，且是真实、临床相关（治疗革兰氏阳性菌感染）、立体化学丰富（7 个非标准氨基酸残基 + 糖基化修饰）的抗生素超分子体系，其二聚化正是抗菌机制的关键环节。RCSB PDB 公开数据，取得方式与本会话生物域已用 PDB 结构一致。
- **候选筛选过程**：最初考虑间苯二酚杯芳烃六聚体胶囊（COD 7230210，Atwood/MacGillivray 家族的经典超分子胶囊），但其 CIF 高达 566KB、755 个不对称单元原子位点、化学式含非整数（H59.33、O12.67，表明连续/平均化的溶剂-客体无序），判断在本批范围内难以可靠清理，改选无序更简单（标准两构象 altLoc 对，非连续平均）的 1AA5。这一权衡过程记录在 sources.json 中，不是事后合理化。
- **无序处理**：1AA5 是 0.89Å 超高分辨率结构，部分侧链/糖环原子有标准的双构象无序（altLoc A/B，占位互补如 0.74/0.26），本批只取主占位分量，已在证据记录中明确披露；结晶水、氯离子、乙酸等非万古霉素原子已排除。
- **内容**（5 感知 + 5 推断，设计=0）：**全局尺度**族 CNP007/008/009（单体A/单体B/完整二聚体穷举扫描），复用生物/量子/材料域已验证的全局尺度方法族，首次应用于真实复杂小分子抗生素；**最近接触**族 CNP010（新设计但简单：两链间穷举扫描找最近原子对，恰好是 O···H 短接触，与氢键相符），与"全局最大间距"互补；**回转半径**族 CNP011（复用 BNP002/QNP010/QNP011 公式）。推断题：**末端 vs 全局尺度**族 CNI002/003（复用 BNP001 方法族，序列首尾 CA-CA 距离 vs Dmax）；**链间 Rg 比较**族 CNI004（新设计：直接联系原始论文标题"不对称二聚体"表述，检验单一标量比较的证据强度边界，结果显示两链 Rg 极接近——弱证据，不足以单独证实或证伪"不对称"表述）；**尺度算术推理**族 CNI005（新设计：引用已算出的三个 Dmax 值，推理二聚体是并排/背靠背而非首尾伸展缔合）；**证据边界**族 CNI006（新设计：区分"观测到的几何事实"（短 O···H 距离）与其常被用来支持的更强化学论断（氢键、文献记载的二聚界面），明确后者各自还需要的额外证据——延续本会话 QNI008/MNI010 已建立的认识论纪律）。
- **复核**：`runs/chem-nm-v04-001/independent_checks.py` 从零重写 PDB 解析器（不导入 compute_chem_nm.py），用 Decimal 精度独立重新读取原始 1AA5.pdb；10/10 全部通过。
- **产物**：runs/chem-nm-v04-001/（含 build_bundle.py/compute_chem_nm.py/author_*.py/independent_checks.py/publish_assets_and_catalog.py 系列作者脚本）、新页面 docs/chem-nm-batch.html、docs/assets/qa/ 下 10 道题共约 15 个 xyz 附件 + 10 个 input.txt、docs/data/traces/{CNP007,CNP008,CNP009,CNP010,CNP011,CNI002,CNI003,CNI004,CNI005,CNI006}.json、tests/test_chem_nm_geometry.py（11 项新测试，全部从已提交的 docs/assets/qa/ 读取，不依赖 runs/）。
- **未提交内容**：原始 PDB 文件（1AA5.pdb，约 98KB，RCSB 公开数据）留在本机 runs/chem-nm-v04-001/materials/，gitignored；异机接手可直接从 files.rcsb.org 按 PDB ID 重新下载。

## 实际执行的检查（全会话）

- `python -m unittest discover -s tests -v`：**141 项全部通过**（初始 63 → +6 材料 +8 生物(v2) +5 化学 +14 生物(v3/4/5) +10 量子(0.1-1nm) +12 量子(1-10nm) +12 材料(1-10nm) +11 化学(1-10nm) = 141）。
- `tools/export_prototype.py` / `export_admission_audit.py` / `export_modules.py`：每个子批次后都重跑成功，最终状态见上方覆盖表。
- 本地起 HTTP 服务器（Python `http.server`）+ 浏览器实测：index.html 候选列表（80 道全部可见）、audit.html 16 格覆盖表（四领域 0.1–1nm 与 1–10nm 共 8 行均显示 10/10）、trace.html 对新题的 M0–M6 生成记录、八个批次报告页（materials-batch.html / bio-batch.html / chem-local-batch.html / quantum-batch.html / quantum-nm-batch.html / materials-nm-batch.html / chem-nm-batch.html）新区块渲染、全部新增静态资源（.xyz/输入文本/JSON）返回 200。
- 本会话额外验证了 GitHub Pages 线上部署（见量子1-10nm批次记录）：用户报告网站上看不到新内容，排查后确认是 CDN 边缘缓存传播延迟（部署记录显示 push 后约 1-2 分钟已触发新部署，只是首次抓取命中了未刷新的缓存节点），几分钟后重新抓取已显示最新数据；此后每批仍只做本地服务器验证，未逐批重复线上验证。
- 过程中发现并修复三处小问题：① audit.html 里因遗漏 `</p><p>` 换行导致两个入口链接粘连；② test_materials_batch2.py 依赖被 Git 忽略目录的可移植性 bug；③ construction 阶段 evidence_review 路由要求 `units` 字段必须为空字符串、evidence 阶段 `asset_ids` 必须只含 xyz 类型来源（量子1-10nm批次）；④ `Decimal.__mod__` 不自动包裹负值到 [0,1)（材料1-10nm批次独立复核脚本中发现并修复）。
- **未做**：专家审核、模型难度试测。所有新题 status 均为 pending_human_audit，未擅自改动任何题目的人工审核状态。

## 下一项工作（给下一位接手者）

**八格已满，四领域的两个起步尺度格（0.1–1nm、1–10nm）全部见底**：材料×0.1–1nm、材料×1–10nm、化学×0.1–1nm、化学×1–10nm、生物×0.1–1nm、生物×1–10nm、量子×0.1–1nm、量子×1–10nm。剩余 80 个缺口全部集中在 10–100nm 与 100–1000nm 两个更大尺度格（每领域各 2 格，共 8 格）。量子/材料/化学三次突破 1nm 起步格都遵循同一模式："引入专门覆盖更大尺度的新数据源" + "用全局尺度/晶胞级/整分子级方法代替局部键角方法"，三次成功验证了这条路径的可靠性；生物域 1–10nm 格本会话开始时已有 5/10，本会话用已有 PDB 结构补满剩余 5 道，未额外引入新数据源。

**建议优先级**（按可行性从高到低）：

1. **10–100nm 尺度格是下一个真正的挑战**：三次 1nm+ 突破用的数据源（OE62 最大分子约 174 原子/~2-3nm；MOF 晶胞展开约 200-400 原子/~3-4nm；万古霉素二聚体 264 原子/~2.9nm）全部止步在个位数 nm，没有一个天然接近 10nm，更不用说 10-100nm。这不是简单地"再找一个稍大的分子"就能解决，需要从根本上换一类对象：
   - **材料域**：真实纳米颗粒模型（金纳米团簇如 Au144(SR)60、量子点核壳结构）、多晶胞超胞、更大孔径的 MOF/沸石。
   - **量子域**：聚合物链段（真实、非理想化的均聚物/共聚物晶体或分子动力学快照）、更大的超分子组装体电子结构数据集。
   - **化学域**：树状大分子（dendrimer）晶体结构、更大的自组装胶囊/笼状结构（本次因无序过重而放弃的间苯二酚杯芳烃六聚体胶囊，若愿意投入更多时间清理 disorder，仍是一个真实候选）。
   - **生物域**：病毒衣壳、核糖体、更大的多亚基复合物（真实结构数据可能来自冷冻电镜 PDB/EMDB 条目，坐标量级可能达到数千到数万原子，需评估可行的题目设计与计算规模）。
2. **100–1000nm 格更进一步**：单个分子/复合物结构数据在这个尺度基本不存在（超出常规晶体学/冷冻电镜的常见报道范围），可能需要考虑纳米颗粒集合体、脂质体、病毒颗粒整体等更接近"颗粒/组装体尺寸"而非"单一原子分辨率结构"的对象，这类数据往往不含原子级坐标，题目设计思路可能需要根本性调整（例如从原子坐标几何转向粒径分布、散射长度等间接几何量），值得在开始前与用户讨论方向。
3. **"复用已验证结构挖掘局部特征"与"全局尺度/整对象方法"这两条思路都已在 1nm 以内格与 1-10nm 格用尽**：不要在 10nm+ 格重复同样的方法论，需要真正更大尺度的真实材料。

**执行规范**（继续遵循 AGENTS.md/CLAUDE.md）：先确认来源、材料和验证器，再跑新批次；允许不足，不为凑齐设计题降低验证标准；每批完成后更新本文件、跑测试、跑三个 export 脚本、本地起服务器核实渲染、提交前 `git fetch` 确认无分叉。用户已明确批次数量不设固定上限，由助手依材料可得性和验证质量自行判断规模。鉴于 10nm+ 格的难度显著提升，下一位接手者可能需要先与用户讨论可行的数据源方向，而不是直接假设现有方法论可以平移。

## 提交/远端同步/Pages 状态

- 每次提交前均 `git fetch` 确认与 origin/main 一致（全程无分叉）。
- 全部提交均已推送：`8f9d138` → `7a5f96a` → `8ded5f0` → `2e35100` → `58b54cd` → `5514a49` → `387915b` → `44a01e5` → `f309aab` → `5ca3114` → `538e775`（当前 HEAD）。
- **Pages 部署已在本会话验证**（量子1-10nm批次）：确认 GitHub Pages 从 main 分支 /docs 目录自动部署，push 后约 1-2 分钟触发新部署；线上 `https://k0ng1212.github.io/geometry-qa-builder/` 内容与本地仓库一致，只是偶尔有几分钟的 CDN 边缘缓存传播延迟，不是配置问题。

## 接手时哪些东西可获得

| 位置 | 用途与限制 |
|---|---|
| GitHub 仓库 | 代码、规则、公开题目、附件和公开 trace；可在新机器使用 |
| 本地 runs/<run-id>/ | 冻结 pipeline、packet、context、全部阶段结果、报告；只有这份才可恢复原运行（本会话 13 个新 run 均在本机 runs/ 下：materials-cell-v04-002、bio-nm-v04-002/003/004/005、chem-local-v04-003、q02-force-v04-002、quantum-nm-v04-001/002、materials-nm-v04-001、chem-nm-v04-001） |
| 本地 inputs/ 及仓库外工作目录 | 部分原始下载和辅助脚本；不随 Git 同步 |
| docs/data/traces/<QA-ID>.json | 脱敏公开摘录，不能当成完整恢复包 |

同机接手可直接用 runs/ 下的 13 个新 run（本会话在同一台电脑完成）。异机接手：本会话新增的题目材料来源都是公开的（COD/RCSB PDB/SAMPL9 GitHub/Zenodo QM7-X/TUM mediaTUM OE62/crystallography.net MOF CIF），可重新检索获取，不依赖任何私有材料；但 runs/ 下的完整冻结记录不会同步（包括量子×0.1–1nm 批次本地缓存的 8000.hdf5 826MB、量子×1–10nm 批次本地缓存的 df_62k.json 387MB + df_5k.json 51MB，均未提交），只能参考已发布的 docs/ 内容新建 run。OE62 的 mediaTUM 网页本身访问受限，需改用其官方 FTP 端点（sources.json 中记录了完整地址和 SHA512 校验值）；materials-nm-v04-001 的两份 CIF 与 chem-nm-v04-001 的 PDB 文件体积都很小（各约 11-98KB），异机接手直接从 crystallography.net（COD ID 4118891、1516287）或 files.rcsb.org（PDB ID 1AA5）重新下载即可，没有 OE62 那样的访问限制。

## 每次交接更新模板

- 日期、执行助手、任务和所基于的提交：
- 本次新增/修改的题号与 run ID：
- 当前阶段及已保存输入输出位置：
- 来源、计算/评分方法及限制：
- 实际执行的检查与结果（未执行也说明）：
- 初筛数、人工待审数、已明确人工确认的题号：
- 未完成事项、原因、下一步：
- 提交/远端同步/Pages 状态（分别说明；可记录上一批提交或用 Git HEAD，避免自引用哈希）：
