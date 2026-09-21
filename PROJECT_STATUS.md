# 当前交接状态

更新：2026-09-21，执行助手 Claude Sonnet 5（Claude Code 会话，claude-sonnet-5）。本文件是这次会话六轮工作的**合并总结**（此前分批提交逐步更新，现整合为一份连贯记录，方便下一位助手/智能体接手）。

**用户指示**：读取 CLAUDE.md/PROJECT_STATUS.md 核对状态后，按现有 Builder 继续生成候选题；数量不设 6 道上限，由助手自行判断规模；用户随后四次说"继续"/"再做一批吧，这次多做点，不用在意运行时间"/"继续做下一批,量子1-10nm"。

**本次会话总产出**：新增 **41 道**候选题（19→60，占目标 160 的比例从 12% 提升到 38%），补满 **6 个尺度格**（材料×0.1–1nm、化学×0.1–1nm、生物×0.1–1nm、生物×1–10nm、量子×0.1–1nm、量子×1–10nm），全部走完整 M0–M6、双方法独立复核、pending_human_audit。前 5 批已推送到 origin/main；第 6 批（quantum-nm，量子 1–10nm）为本次更新新增，见下方提交表最后一行：

| 提交 | 内容 | 新增题数 |
|---|---|---:|
| `8f9d138` | materials-cell-v04-002（MgO/CsCl 新 COD 结构） | 4 |
| `7a5f96a` | bio-nm-v04-002（6LYZ/1EHZ 新 PDB 结构，本项目首个 RNA） | 5 |
| `8ded5f0` | chem-local-v04-003（SAMPL9 H26DM-B-CD 新结构）+ 修复测试可移植性 bug | 3 |
| `2e35100` | bio-nm-v04-003/004/005（复用已验证结构，挖掘亚纳米局部几何，零新检索） | 10 |
| `58b54cd`→`5514a49` | q02-force-v04-002（QM7-X 新增 5 分子，量子×0.1–1nm 补满） | 9 |
| (本次提交) | quantum-nm-v04-001/002（OE62 数据集新引入，量子×1–10nm 补满） | 10 |

## 当前基线

- HEAD：本次提交（quantum-nm-v04-001/002），父提交 `5514a49`。
- 构题标准：PROTOTYPE.md 和 builder_modules/m0_scope/prototype-policy.json 的 v0.4，本会话未变更任何 Builder 代码逻辑（仅新增复算/发布脚本，属于既定模式的延伸）。本批次首次引入 OE62 数据集（此前只用过 QM7-X/COD/RCSB PDB/SAMPL9），全部题目走 evidence_review（全局尺度扫描、回转半径、能隙提取/比较均非 xyz_distance/xyz_angle 注册验证器类型）。
- 目标 160，完整初筛候选 **60**，缺 100；正式可用计数仍为 0（无专家审核）。60 条均 pending_human_audit。
- 31 个旧规划方向及 33 条历史记录不计入当前候选；本会话未触碰这些历史记录。

## 16 格覆盖现状（docs/audit.html 实时数据，docs/data/prototype-progress.json 来源）

| 领域 | 0.1–1 nm | 1–10 nm | 10–100 nm | 100–1000 nm |
|---|---:|---:|---:|---:|
| 量子/电子结构 | **10/10** ✅ | **10/10** ✅ | 0/10 | 0/10 |
| 化学 | **10/10** ✅ | 0/10 | 0/10 | 0/10 |
| 材料 | **10/10** ✅ | 0/10 | 0/10 | 0/10 |
| 生物 | **10/10** ✅ | **10/10** ✅ | 0/10 | 0/10 |

本会话前状态：材料 6/10、化学 7/10、生物 0.1–1nm 0/10、生物 1–10nm 5/10、量子 0.1–1nm 1/10、量子 1–10nm 0/10。六格全部由本会话补满。0.1–1nm 起步格（量子/化学/材料）与生物两格现已全部见底；量子 1–10nm 是本会话第一个突破 0.1–1nm 起步格的尺度格。

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

## 实际执行的检查（全会话）

- `python -m unittest discover -s tests -v`：**118 项全部通过**（初始 63 → +6 材料 +8 生物(v2) +5 化学 +14 生物(v3/4/5) +10 量子(0.1-1nm) +12 量子(1-10nm) = 118）。
- `tools/export_prototype.py` / `export_admission_audit.py` / `export_modules.py`：每个子批次后都重跑成功，最终状态见上方覆盖表。
- 本地起 HTTP 服务器（Python `http.server`）+ 浏览器实测：index.html 候选列表（60 道全部可见）、audit.html 16 格覆盖表（量子两行均显示 10/10）、trace.html 对新题的 M0–M6 生成记录（含 QNI008 两份分子附件）、六个批次报告页（materials-batch.html / bio-batch.html / chem-local-batch.html / quantum-batch.html / quantum-nm-batch.html）新区块渲染、全部新增静态资源（.xyz/输入文本/JSON）返回 200。
- 过程中发现并修复两处小问题：① audit.html 里因遗漏 `</p><p>` 换行导致两个入口链接粘连；② 上述 test_materials_batch2.py 依赖被 Git 忽略目录的可移植性 bug。本批次另发现并修复：construction 阶段 evidence_review 路由要求 `units` 字段必须为空字符串（回转半径题最初误填 'angstrom'）、evidence 阶段 `asset_ids` 必须只含 xyz 类型来源（能隙证据最初误把能级文本来源也列入）。
- **未做**：专家审核、模型难度试测。所有新题 status 均为 pending_human_audit，未擅自改动任何题目的人工审核状态。

## 下一项工作（给下一位接手者）

**六格已满**：材料×0.1–1nm、化学×0.1–1nm、生物×0.1–1nm、生物×1–10nm、量子×0.1–1nm、量子×1–10nm。三域（量子/化学/材料）的 0.1–1nm 起步格与生物两格全部见底；**量子域已突破到 1–10nm**，证明"起步格用尽后引入全新数据源继续推进"这条路径可行。剩余 100 个缺口中，化学/材料/生物各缺 3 个 1nm 以上尺度格，量子缺 2 个（10–100nm、100–1000nm）。

**建议优先级**（按可行性从高到低）：

1. **化学/材料域 1–10nm 格**：可参照量子域本次的思路——SAMPL9/COD 现有材料天然偏小，需要新数据源。材料域可考虑更大的周期性超胞或纳米颗粒模型；化学域 bCD guest_files 目录下 CPZ/PMT/PMZ/TDZ/TFP 等真实药物分子仍未使用，但需先核实其尺度是否真的达到 1nm（未必，多数药物分子仍在 0.1–1nm）。
2. **"复用已验证结构挖掘局部特征"这条思路已在 0.1–1nm 格用尽**：材料域 COD 结构、化学域 SAMPL9 host/guest、QM7-X 分子内局部几何均已挖掘出多道题；**这条捷径填不了 1nm 以上的格**，因为局部特征的推理尺度本质上受限于原子间距量级——量子域这次改用"全局尺度/回转半径"（跨越整个大分子的性质，而非局部键角）加"引入专门覆盖更大分子的新数据集"才突破了这个限制，这条经验可推广到其他领域。
3. **量子域 10–100nm 与 100–1000nm 格**：OE62 最大分子约 174 原子，可能仍不够大；需要更大尺度的数据源（如聚合物链段、超分子组装体的量子化学数据），本会话未探索。
4. **化学/材料/生物/量子的 100–1000nm 尺度格**（共 4 格）：全新尺度，需要真正更大尺度的真实材料（纳米颗粒、超胞、超分子组装体、大分子复合物等），local-feature 挖掘方法不适用。

**执行规范**（继续遵循 AGENTS.md/CLAUDE.md）：先确认来源、材料和验证器，再跑新批次；允许不足，不为凑齐设计题降低验证标准；每批完成后更新本文件、跑测试、跑三个 export 脚本、本地起服务器核实渲染、提交前 `git fetch` 确认无分叉。用户已明确批次数量不设固定上限，由助手依材料可得性和验证质量自行判断规模。

## 提交/远端同步/Pages 状态

- 每次提交前均 `git fetch` 确认与 origin/main 一致（全程无分叉）。
- 前五次提交均已推送：`8f9d138` → `7a5f96a` → `8ded5f0` → `2e35100` → `58b54cd` → `5514a49`。本次 quantum-nm 批次提交见本文件更新后的 `git log` 最新一条；提交前同样执行了 `git fetch` 核对无分叉。
- Pages 部署未在本会话验证（无法访问已部署的 GitHub Pages URL），仅本地服务器验证过静态资源可达，上线情况需下一位助手或用户核实。

## 接手时哪些东西可获得

| 位置 | 用途与限制 |
|---|---|
| GitHub 仓库 | 代码、规则、公开题目、附件和公开 trace；可在新机器使用 |
| 本地 runs/<run-id>/ | 冻结 pipeline、packet、context、全部阶段结果、报告；只有这份才可恢复原运行（本会话 11 个新 run 均在本机 runs/ 下：materials-cell-v04-002、bio-nm-v04-002/003/004/005、chem-local-v04-003、q02-force-v04-002、quantum-nm-v04-001/002） |
| 本地 inputs/ 及仓库外工作目录 | 部分原始下载和辅助脚本；不随 Git 同步 |
| docs/data/traces/<QA-ID>.json | 脱敏公开摘录，不能当成完整恢复包 |

同机接手可直接用 runs/ 下的 11 个新 run（本会话在同一台电脑完成）。异机接手：本会话新增的题目材料来源都是公开的（COD/RCSB PDB/SAMPL9 GitHub/Zenodo QM7-X/TUM mediaTUM OE62），可重新检索获取，不依赖任何私有材料；但 runs/ 下的完整冻结记录不会同步（包括量子×0.1–1nm 批次本地缓存的 8000.hdf5 826MB、量子×1–10nm 批次本地缓存的 df_62k.json 387MB + df_5k.json 51MB，均未提交），只能参考已发布的 docs/ 内容新建 run。OE62 的 mediaTUM 网页本身访问受限，需改用其官方 FTP 端点（sources.json 中记录了完整地址和 SHA512 校验值）。

## 每次交接更新模板

- 日期、执行助手、任务和所基于的提交：
- 本次新增/修改的题号与 run ID：
- 当前阶段及已保存输入输出位置：
- 来源、计算/评分方法及限制：
- 实际执行的检查与结果（未执行也说明）：
- 初筛数、人工待审数、已明确人工确认的题号：
- 未完成事项、原因、下一步：
- 提交/远端同步/Pages 状态（分别说明；可记录上一批提交或用 Git HEAD，避免自引用哈希）：
