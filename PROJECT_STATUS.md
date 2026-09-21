# 当前交接状态

更新：2026-09-21，执行助手 Claude Sonnet 5（Claude Code 会话，claude-sonnet-5）。本文件是这次会话四轮工作的**合并总结**（此前分四次提交逐步更新，现整合为一份连贯记录，方便下一位助手/智能体接手）。

**用户指示**：读取 CLAUDE.md/PROJECT_STATUS.md 核对状态后，按现有 Builder 继续生成候选题；数量不设 6 道上限，由助手自行判断规模；用户随后两次说"继续"。

**本次会话总产出**：新增 **22 道**候选题（19→41，占目标 160 的比例从 12% 提升到 26%），补满 **4 个尺度格**（材料×0.1–1nm、化学×0.1–1nm、生物×0.1–1nm、生物×1–10nm），全部走完整 M0–M6、双方法独立复核、pending_human_audit。共 4 次提交，均已推送到 origin/main：

| 提交 | 内容 | 新增题数 |
|---|---|---:|
| `8f9d138` | materials-cell-v04-002（MgO/CsCl 新 COD 结构） | 4 |
| `7a5f96a` | bio-nm-v04-002（6LYZ/1EHZ 新 PDB 结构，本项目首个 RNA） | 5 |
| `8ded5f0` | chem-local-v04-003（SAMPL9 H26DM-B-CD 新结构）+ 修复测试可移植性 bug | 3 |
| `2e35100` | bio-nm-v04-003/004/005（复用已验证结构，挖掘亚纳米局部几何，零新检索） | 10 |

## 当前基线

- HEAD：`2e35100`（本会话最后一次提交，已推送）。
- 构题标准：PROTOTYPE.md 和 builder_modules/m0_scope/prototype-policy.json 的 v0.4，本会话未变更任何 Builder 代码逻辑（仅新增 tools/recompute_materials_batch2.py、tools/recompute_bio_batch2.py 两个复算脚本，属于既定模式的延伸）。
- 目标 160，完整初筛候选 **41**，缺 119；正式可用计数仍为 0（无专家审核）。41 条均 pending_human_audit。
- 31 个旧规划方向及 33 条历史记录不计入当前候选；本会话未触碰这些历史记录。

## 16 格覆盖现状（docs/audit.html 实时数据，docs/data/prototype-progress.json 来源）

| 领域 | 0.1–1 nm | 1–10 nm | 10–100 nm | 100–1000 nm |
|---|---:|---:|---:|---:|
| 量子/电子结构 | 1/10 | 0/10 | 0/10 | 0/10 |
| 化学 | **10/10** ✅ | 0/10 | 0/10 | 0/10 |
| 材料 | **10/10** ✅ | 0/10 | 0/10 | 0/10 |
| 生物 | **10/10** ✅ | **10/10** ✅ | 0/10 | 0/10 |

本会话前状态：材料 6/10、化学 7/10、生物 0.1–1nm 0/10、生物 1–10nm 5/10。四格全部由本会话补满。

## 已完成的当前题库（完整清单）

| 批次/本地 run | QA | 数量 |
|---|---|---:|
| prototype-v04-bcd-001 | CNP001 | 1 |
| chem-local-v04-002-r1 | CNP002、CNP003 | 2 |
| **chem-local-v04-003**（本会话） | CNP005、CNP006、CNI001 | 3 |
| q02-force-v04-001 | QNP001 | 1 |
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

## 实际执行的检查（全会话）

- `python -m unittest discover -s tests -v`：**96 项全部通过**（初始 63 → +6 材料 +8 生物(v2) +5 化学 +14 生物(v3/4/5) = 96）。
- `tools/export_prototype.py` / `export_admission_audit.py` / `export_modules.py`：每个子批次后都重跑成功，最终状态见上方覆盖表。
- 本地起 HTTP 服务器（Python `http.server`）+ 浏览器实测：index.html 候选列表（41 道全部可见）、audit.html 16 格覆盖表、trace.html 对新题的 M0–M6 生成记录（含跨批次引用的 CNI001/BNI008）、四个批次报告页（materials-batch.html / bio-batch.html / chem-local-batch.html）新区块渲染、全部新增静态资源（.xyz/.pdb/.cif/输入文本/JSON）返回 200。
- 过程中发现并修复两处小问题：① audit.html 里因遗漏 `</p><p>` 换行导致两个入口链接粘连；② 上述 test_materials_batch2.py 依赖被 Git 忽略目录的可移植性 bug。
- **未做**：专家审核、模型难度试测。所有新题 status 均为 pending_human_audit，未擅自改动任何题目的人工审核状态。

## 下一项工作（给下一位接手者）

**四格已满**：材料×0.1–1nm、化学×0.1–1nm、生物×0.1–1nm、生物×1–10nm。

**建议优先级**（按可行性从高到低）：

1. **"复用已验证结构挖掘局部特征"这条思路可以推广**：材料域的 COD 结构（Si/diamond/NaCl/MgO/CsCl）里可能还有未问过的局部几何（次近邻壳层、非最近邻键角等）；化学域的 SAMPL9 host/guest 复合物若已下载 guest 分子（bCD guest_files 目录下有 CPZ/PMT/PMZ/TDZ/TFP 等真实药物分子，本会话未使用）可能有未测的局部基元。**但这条捷径只能填同一尺度格内的剩余空缺，不能跨尺度**——填 1–1000nm 格仍需全新材料。
2. **量子域**（四格全空，缺口最大）：除 QNP001（QM7-X 数据集）外没有可直接复用的材料/方法，需要新的计算化学数据源；QM7-X 数据集本身可能还有其他分子可挖掘（本会话未探索，QNP001 只用了分子 7001）。
3. **化学/材料/生物的 1–1000nm 三个尺度格**（各领域 3 格，共 9 格）：全新尺度，局部特征挖掘不适用，需要真正更大尺度的真实材料（纳米颗粒、超胞、超分子组装体等）。

**执行规范**（继续遵循 AGENTS.md/CLAUDE.md）：先确认来源、材料和验证器，再跑新批次；允许不足，不为凑齐设计题降低验证标准；每批完成后更新本文件、跑测试、跑三个 export 脚本、本地起服务器核实渲染、提交前 `git fetch` 确认无分叉。用户已明确批次数量不设固定上限，由助手依材料可得性和验证质量自行判断规模。

## 提交/远端同步/Pages 状态

- 每次提交前均 `git fetch` 确认与 origin/main 一致（全程无分叉）。
- 四次提交均已推送：`8f9d138` → `7a5f96a` → `8ded5f0` → `2e35100`（当前 HEAD）。
- Pages 部署未在本会话验证（无法访问已部署的 GitHub Pages URL），仅本地服务器验证过静态资源可达，上线情况需下一位助手或用户核实。

## 接手时哪些东西可获得

| 位置 | 用途与限制 |
|---|---|
| GitHub 仓库 | 代码、规则、公开题目、附件和公开 trace；可在新机器使用 |
| 本地 runs/<run-id>/ | 冻结 pipeline、packet、context、全部阶段结果、报告；只有这份才可恢复原运行（本会话 8 个新 run 均在本机 runs/ 下：materials-cell-v04-002、bio-nm-v04-002/003/004/005、chem-local-v04-003） |
| 本地 inputs/ 及仓库外工作目录 | 部分原始下载和辅助脚本；不随 Git 同步 |
| docs/data/traces/<QA-ID>.json | 脱敏公开摘录，不能当成完整恢复包 |

同机接手可直接用 runs/ 下的 8 个新 run（本会话在同一台电脑完成）。异机接手：本会话新增的题目材料来源都是公开的（COD/RCSB PDB/SAMPL9 GitHub），可重新检索获取，不依赖任何私有材料；但 runs/ 下的完整冻结记录不会同步，只能参考已发布的 docs/ 内容新建 run。

## 每次交接更新模板

- 日期、执行助手、任务和所基于的提交：
- 本次新增/修改的题号与 run ID：
- 当前阶段及已保存输入输出位置：
- 来源、计算/评分方法及限制：
- 实际执行的检查与结果（未执行也说明）：
- 初筛数、人工待审数、已明确人工确认的题号：
- 未完成事项、原因、下一步：
- 提交/远端同步/Pages 状态（分别说明；可记录上一批提交或用 Git HEAD，避免自引用哈希）：
