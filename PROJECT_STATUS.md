# 当前交接状态

更新：2026-09-21，执行助手 Claude Sonnet 5（Claude Code 会话，claude-sonnet-5）。任务：按用户指示读取 CLAUDE.md/PROJECT_STATUS.md 核对状态后，按现有 Builder 继续生成候选题；用户明确表示数量不设 6 道上限，由助手自行判断。本轮共完成两个子批次：materials-cell-v04-002（4 道）与 bio-nm-v04-002（5 道），合计新增 9 道。

## 当前基线

- 本次提交前 HEAD：`8f9d138`（"Add four MgO/CsCl materials QA..."，上一轮已推送）；本次新增 5 道 QA 的提交见 Git 实际记录，本文件不是提交锁。
- 当前构题标准：PROTOTYPE.md 和 builder_modules/m0_scope/prototype-policy.json 的 v0.4，未变更。
- 目标 160，完整初筛候选 28（23+5），缺 132；正式可用计数 0。28 条均待人工审核。
- 31 个旧规划方向及 33 条历史记录不计入当前候选；不要重新放回主图充数。

## 已完成的当前题库

| 批次/本地 run | QA | 数量 |
|---|---|---:|
| prototype-v04-bcd-001 | CNP001 | 1 |
| chem-local-v04-002-r1 | CNP002、CNP003（其他历史记录不自动计入） | 2 |
| q02-force-v04-001 | QNP001 | 1 |
| paper-hbond-v04-001-r1 | HBP001、HBP002、HBI001、HBI002 | 4 |
| bio-nm-v04-001 | BNP001–003、BNI001–002 | 5 |
| materials-cell-v04-001 | MNP001–003、MNI001–003 | 6 |
| materials-cell-v04-002 | MNP004、MNP005、MNI004、MNI005 | 4 |
| bio-nm-v04-002 | BNP004–006、BNI003–004 | 5 |

运行目录均在本仓库本地 runs/ 下且被 Git 忽略。题号归属和当前处置以 docs/data/catalog.json 为准；缺口查 docs/data/prototype-progress.json，审核入口为 docs/audit.html。

## 本轮第一批：materials-cell-v04-002（材料 × 0.1–1 nm，补满至 10/10）

- 2 感知、2 推断、0 设计；材料 × 0.1–1 nm 格由 6/10 补齐到 **10/10**（该格初筛缺口清零）。
- 来源：官方 COD 结构 1000053（MgO periclase，Sasaki/Fujino/Takeuchi 1979，doi:10.2183/pjab.55.43）、9008789（CsCl，Wyckoff 1963，与本项目卤化钠同一来源卷）。原始结构路线，非复用既有 QA；CsCl 原胞仅 2 原子（非本项目此前惯用的 8 原子晶胞），已在题干中明确披露。
- 内容：MgO 岩盐型异种/同种近邻壳层（MNP004）、CsCl 原生纯净立方体角配位壳层（MNP005，配位数 8，新几何类型）、MgO 晶面间距与 Bragg 角（MNI004）、CsCl 结构因子化学对比与体心立方型消光选择定则（MNI005，区分"晶格禁戒"与"化学对比禁戒"两类概念，非既有题模板的重复实例）。
- 计算与复核：新脚本 runs/materials-cell-v04-002/compute_new_materials.py，配套 independent_checks.py 用第二种独立方法交叉核验，4 道全部通过；新增 tests/test_materials_batch2.py（6 项单元测试）。
- 报告：[materials-batch.html](docs/materials-batch.html) 已扩充第二批区块；来源/计算见 docs/data/materials-batch-v2-*.json；原 CIF 在 docs/assets/materials/；题目附件在 docs/assets/qa/；公开模块摘录在 docs/data/traces/；处置记录见 docs/data/qa-disposition.md。
- 曾尝试寻找 GaAs 闪锌矿和单质铜条目补充覆盖，均未在会话时间内定位到干净可用的 COD 记录，已如实记录在 runs/materials-cell-v04-002/sources.json，留给后续批次。

## 本轮第二批：bio-nm-v04-002（生物 × 1–10 nm，补满至 10/10）

- 3 感知、2 推断、0 设计；生物 × 1–10 nm 格由 5/10 补齐到 **10/10**（该格初筛缺口清零）。
- 来源：官方 RCSB PDB 结构 6LYZ（鸡蛋清溶菌酶，Diamond 1974 real-space refinement 经典结构，129 个 Cα）、1EHZ（酵母苯丙氨酸 tRNA，Shi & Moore 2000，1.93 Å，76 个 C1′，其中 14 个修饰核苷酸以 HETATM 记录、已核实合并为无缺口骨架）。这是本项目第一次使用 RNA 结构，补上蛋白质/DNA 之外的第三类真实生物大分子。
- 内容：溶菌酶端距/最大尺寸/催化裂隙（Glu35–Asp52，身份由条目自带 HELIX 与立体化学核查记录独立确认，BNP004）、tRNA 骨架路径长度是端到端直线距离的约 24 倍（L 形折叠的直接几何证据，BNP005）、反密码子三联体局部构象（134.53°，非完全共线，与 SEQRES 记录核对身份为 OMG-A-A，BNP006）、溶菌酶与已通过的 1UBQ/1CRN 三者回转半径比较（复用旧批次已发表数值，未重算，BNI003）、tRNA 受体端到反密码子的虚拟 FRET 探针量程不匹配推断（r≈7.23nm 远超 R0=3.5nm 有效范围，效率降到约 0.0127，属实验设计类推断而非单纯代公式，BNI004）。
- 计算与复核：新工具 tools/recompute_bio_batch2.py（延续 tools/recompute_bio_batch.py 风格，独立于其硬编码三结构版本），内建双重验证（全扫描 vs 原方法、pairwise-distance 恒等式 Rg、atan2 夹角、Decimal 精度 FRET）；新增 tests/test_bio_geometry2.py（8 项单元测试）。
- 报告：[bio-batch.html](docs/bio-batch.html) 已扩充第二批区块；来源/计算见 docs/data/bio-batch-v2-*.json；原始 PDB 在 docs/assets/bio/；题目附件在 docs/assets/qa/；公开模块摘录在 docs/data/traces/；处置记录见 docs/data/qa-disposition.md。

## 实际执行的检查（两批共同）

- `python -m unittest discover -s tests -v` 全部 77 项通过（63 旧 + 6 材料新 + 8 生物新）。
- `tools/export_prototype.py`/`export_admission_audit.py`/`export_modules.py` 均重跑成功。
- 本地起 HTTP 服务器用浏览器核对了 index.html 候选列表（28 道）、audit.html 16 格覆盖表（材料/生物两格均 10/10）、trace.html 对新题的 M0–M6 记录、materials-batch.html 与 bio-batch.html 新区块、以及全部新增静态资源（.xyz/.pdb/.cif/输入文本/JSON）的 200 响应；同步更新了 audit.html 中两处指向批次报告的静态入口文字。
- 未做专家审核或模型难度试测。初筛数 28、人工待审 28、无已明确人工确认的题号（与上一份交接记录一致，用户此前提到"审核了几条"但未指定编号，未据此改状态）。

## 下一项工作

材料 × 0.1–1 nm、生物 × 1–10 nm 两格已补满。下一步按覆盖统计（docs/audit.html 16 格表）选缺口继续：量子域全部四格（各 9–10 缺口，最大空白）、化学 1–1000 nm 三格（各 10 缺口）、材料 1–1000 nm 三格（各 10 缺口）、生物 0.1–1 nm 及 10–1000 nm（各 9–10 缺口）都是空白。化学 0.1–1 nm 还差 3（已有 11 条 located、7 screened，其余为 rework/backlog 历史条目，需先核实是否可重构而非直接复用）。继续遵循：先确认来源、材料和验证器，再跑新批次；允许不足，不为凑齐设计题降低验证标准。用户已明确本轮批次数量不设固定上限，由助手依材料可得性和验证质量自行判断规模。

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
