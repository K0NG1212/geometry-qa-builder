# 许可审计（W2，2026-11-02）

上传 Hugging Face 之前，逐来源核对「我们从它那里发布了什么、它的许可允许什么、许可写在哪」。
数据由 `tools/export_license_audit.py` 生成到 [docs/data/license-audit.json](docs/data/license-audit.json)，
规则由 [tests/test_license.py](tests/test_license.py) 钉住。本页只写审计出来的结论，不替任何来源断定许可。

## 结论

| | |
|---|---|
| 来源 | 37 个（336 道在库题 + 1 张已发布但未用的卡） |
| 不可发布 | **0 个** |
| 可直接发布 | 22 个 |
| 上传前要复核 | 14 个（原因见下，都不是阻塞项） |
| 要先做决定的 | **1 个：OE62（CC BY-SA 4.0）** |

一句话：**没有发现「不能转载却转载了」的来源**；真正要定的只有 OE62 的相同方式共享，以及 16 张证据／设计卡里几处逐词相同的短句要改写。

## 为什么要分三类看

同一批题，从来源拿的东西完全不同，只有第一类才是「转载」问题：

| 类别 | 道数 | 含义 | 许可要求 |
|---|---|---|---|
| 上游坐标 | 239 | 附件里的数字是来源自己的（照抄、对称展开、约简成质心、刚性旋转、转格式） | 必须允许再分发 |
| 本项目坐标 | 55 | 几何是本项目按论文印出的标量（晶格常数、转角、螺距）造的 | 不依赖来源许可 |
| 本项目转述 | 42 | 证据卡／设计卡：本项目转述的事实与数值，每条带原文位置 | 事实不受保护，但句子不能逐词照搬 |

## 逐来源

「许可出处」= 谁说的。**出版方副本**指论文本机副本里出版方自己的声明（JATS `<permissions>` 块，或 PDF 上的许可行）；
**仅本项目记录** 指只有我们下载时记下来的那一条（`sources.json` / trace），上传前应再看一眼来源页面。

| 来源 | 道数 | 发布什么 | 许可 | 许可出处 | 判定 |
|---|---|---|---|---|---|
| RCSB PDB / wwPDB | 99 | 上游坐标 99 | CC0 1.0 | 仅本项目记录 | 上传前复核 |
| Crystallography Open Database | 52 | 上游坐标 52 | 公有领域（COD 贡献者声明） | 仅本项目记录 | 上传前复核 |
| QM7-X（Zenodo 4288677） | 31 | 上游坐标 31 | CC BY 4.0 | 仅本项目记录 | 上传前复核 |
| SAMPL9 挑战赛（samplchallenges/SAMPL9） | 13 | 上游坐标 13 | CC BY 4.0 | 仅本项目记录 | 上传前复核 |
| Cao et al., Nature 556, 43 (2018) / arXiv:1803.02342 | 11 | 本项目坐标 7、本项目转述 4 | arXiv 非独占许可 | 仅本项目记录 | 上传前复核 |
| Landscape17（Figshare 29949230） | 11 | 上游坐标 11 | CC BY 4.0 | 仅本项目记录 | 上传前复核 |
| Cottet et al., arXiv:1401.4062 | 10 | 本项目坐标 8、本项目转述 2 | arXiv 非独占许可 | 仅本项目记录 | 上传前复核 |
| Hill et al., Nano Lett. 8, 2341 (2008) | 10 | 本项目坐标 10 | 不依赖许可（只用事实数值） | 不依赖 | 可发布 |
| Shaban et al., Materials 17, 5080 (2024) | 10 | 本项目坐标 8、本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| RCSB PDB / wwPDB（DNA 折纸） | 10 | 上游坐标 10 | CC0 1.0 | 仅本项目记录 | 上传前复核 |
| Crystallography Open Database（MOF） | 9 | 上游坐标 9 | 公有领域（COD 贡献者声明） | 仅本项目记录 | 上传前复核 |
| Altun, Bleda & Trindle, Molecules 26, 2623 (2021) | 9 | 本项目转述 4、上游坐标 5 | CC BY 4.0 | 出版方副本 | 可发布 |
| Kerelsky et al., Nature 572, 95 (2019) / arXiv:1812.08776 | 7 | 本项目坐标 3、本项目转述 4 | arXiv 非独占许可 | 仅本项目记录 | 上传前复核 |
| Gazmeh et al., Sci. Rep. 15, 38349 (2025) | 7 | 本项目坐标 7 | CC BY-NC-ND 4.0 | 出版方副本 | 可发布 |
| **OE62（TUM mediaTUM 1507656）** | **5** | **上游坐标 5** | **CC BY-SA 4.0** | 仅本项目记录 | **待定** |
| Yu, Qu, Guo & Peng, Chem. Mater. 15, 2854 (2003) | 5 | 本项目坐标 5 | 不依赖许可（只用事实数值） | 不依赖 | 可发布 |
| Fookes, Polo Parada & Fidalgo, Sensors 23, 1433 (2023) | 4 | 本项目坐标 3、本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| RCSB PDB 1AA5 | 4 | 上游坐标 4 | CC0 1.0 | 仅本项目记录 | 上传前复核 |
| Dinç et al., Org. Chem. Front. (2024) | 3 | 本项目坐标 2、本项目转述 1 | CC BY 3.0 | 出版方副本 | 可发布 |
| Jiang et al., Nature 521, 545 (2015) | 3 | 本项目转述 3 | PMC 作者稿（非 CC） | 出版方副本 | 上传前复核 |
| Schäfermeier et al., arXiv:2602.13060 | 3 | 本项目坐标 2、本项目转述 1 | CC BY-NC-ND 4.0 | 仅本项目记录 | 可发布 |
| Blom et al., Molecules 21, 16 (2015) | 2 | 本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| Chetry et al., ACS Appl. Mater. Interfaces (2026) | 2 | 本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| Filip et al., Nat. Commun. 5, 5757 (2014) | 2 | 本项目转述 2 | 版权归出版方，保留所有权利 | 出版方副本 | 上传前复核 |
| Rando et al., Chem. Sci. (2025) | 2 | 本项目转述 2 | CC BY 3.0 ← 原记作 4.0 | 出版方副本 | 可发布 |
| Vincent et al., Chem. Eur. J. (2025) | 2 | 本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| Cuello et al., eLife 6, e28032 (2017) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Della Sala et al., Chem. Sci. 12, 9952 (2021) | 1 | 本项目转述 1 | CC BY 3.0 | 出版方副本 | 可发布 |
| Gómez-González et al., Pharmaceutics 14, 60 (2021) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Ikeda et al., Membranes 11, 627 (2021) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Kaabel et al., Chem. Sci. 8, 2184 (2017) | 1 | 本项目转述 1 | CC BY 3.0 | 出版方副本 | 可发布 |
| Mühlbauer et al., Science 323, 915 (2009) / arXiv:0902.1968 | 1 | 本项目转述 1 | arXiv 非独占许可 | 仅本项目记录 | 可发布 |
| Rasmussen et al., Nature 477, 549 (2011) | 1 | 本项目转述 1 | PMC 作者稿（非 CC） | 出版方副本 | 上传前复核 |
| Shuto et al., JACS Au 3, 2905 (2023) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Wilde et al., Sci. Rep. 7, 45941 (2017) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Zhai et al., ACS Cent. Sci. 11, 1753 (2025) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Kim et al., Int. J. Mol. Sci. 25, 9919 (2024) | 0 | 卡片已发布，无在库题 | CC BY 4.0 | 出版方副本 | 可发布 |

**四个 arXiv 预印本（Cao、Kerelsky、Cottet、Mühlbauer）要说清楚一件事**：arXiv 的非独占许可是作者授权 arXiv 分发，
**不是**授权第三方转载。这四篇我们一个字都没转载，依据是「事实与数值不受版权保护」，不是依据许可。表里的许可名只是记录现状。

## 必须做出的决定：OE62

OE62 是 **CC BY-SA 4.0**（相同方式共享），而 QNP023–QNP027 这 5 道发布了它的 `xyz_pbe_relaxed` 坐标原样。
相同方式共享要求「改编作品以相同许可发布」，这会和整库许可相互作用，所以必须先定，三条路：

| 路 | 做法 | 代价 |
|---|---|---|
| ① 整库 CC BY-SA 4.0 | 最省事，一次定清 | 传染性许可，别人拿去做闭源训练集会犹豫，影响采用 |
| ② 主库 CC BY 4.0 + OE62 单列子集 CC BY-SA 4.0（**建议**） | 5 道单独一个 split，许可写在 split 上 | 要在数据卡里解释两段许可 |
| ③ 撤掉这 5 道 | 一刀两断 | 量子 × 1–10 nm 格从 10 道掉到 5 道，这格本来就是最难填的 |

补充事实：这 5 道全在「量子 × 1–10 nm」格，该格共 10 道（另 5 道是 QND008/009、QNI014/015/016，来自 QM7-X 与 COD，许可无问题）。

## 上传前的核对清单

1. **8 个数据库／数据集的许可，只有我们自己的记录**（PDB×3、COD×2、QM7-X、OE62、Landscape17、SAMPL9）。
   逐个到来源页面看一眼，把看到的原话和日期写进对应的 `sources.json`。PDB 的 CC0 与 COD 的公有领域风险极低，但记录要补。
2. **Rando 2025 的许可对不上**：仓库记作 CC BY 4.0，论文自带的 JATS 许可块写的是 CC BY 3.0。以出版方页面为准，确认后统一改
   （`docs/assets/families/design/sources.json`、三份卡片、`templates/family-manifest.json`）。
3. **Schäfermeier 2026 的 CC BY-NC-ND 无法本机核对**（arXiv PDF 里没有许可行）。我们只用数值，所以不影响发布，
   但 `vortex/sources.json` 里的这条声明要在 arXiv 摘要页确认一次。
4. **COD 的引用要求**：COD 文件头要求引用原始文献，52 道里只有 9 道在许可字段记了原始文献。数据卡里要么逐条补，要么统一说明。
5. **16 张卡里有逐词相同的短句要改写**（下节）。

## 要改写的卡（逐词重合 ≥ 8 词）

比对方法：把每张卡在考生那里可见的句子（`topic` / `ask` / `setting` / `goal` / `facts[].text` / 结论）与论文全文都切成词，
找最长的连续相同词串。阈值 8 词：技术短句不可避免会重合（"the critical current is largest at B = 0"），8 词以上就不再是转述。
全部 49 张卡都比对了，没有漏（**0 张未检**；21 个来源的本机副本可用于核对出版方声明）。最长 12 词，没有一张到整句。

| 词数 | 卡片 | 来源许可 | 优先级 |
|---|---|---|---|
| 12 | `filip2014-rbcs.json` | 版权归出版方 | **高** |
| 11 | `kerelsky2019-gap.json` | arXiv 非独占 | **高** |
| 10 | `jiang2015-clamp.json`、`jiang2015-sequence.json` | PMC 作者稿 | **高** |
| 9 | `jiang2015-channel.json` | PMC 作者稿 | **高** |
| 9 | `rasmussen2011-domain.json` | PMC 作者稿 | **高** |
| 9 | `cao2018-squid.json` | arXiv 非独占 | **高** |
| 8 | `cottet2014-bend.json` | arXiv 非独占 | **高** |
| 10 | `ikeda2021-zeolite-pore-ptr.json`、`zhai2025-lectin-sugar-ptr.json` | CC BY 4.0 | 低（许可允许，只为整洁） |
| 10 | `vincent2025-walls*.json`、`vincent2025-viologen*.json`（4 份） | CC BY 4.0 | 低 |
| 9 | `kim2024-ace2-disulfide-ptr.json` | CC BY 4.0 | 低（且未用于在库题） |
| 8 | `shaban2024-ions.json` | CC BY 4.0 | 低（重合的是一串数字） |

**优先级高的 8 张**来自不允许转载原文的来源，改写由 L1 在人工审核时做；CC BY 的来源允许署名转载，改写只是为了口径一致。
改卡片会变动已发布资产的哈希，所以和 11/05–11/08 的重跑一起做。

## 本次已改 / 等重跑

**已改**（`templates/family-manifest.json`，25 条）：

| 改了什么 | 条数 |
|---|---|
| 补上空白许可：OE62 5 条、COD MOF 3 条、PDB 1AA5 4 条 | 12 |
| SAMPL9 由「MIT」改为「非软件材料 CC BY 4.0」 | 13 |

SAMPL9 的 MIT 是错的：其 README 的 LICENSE 节写明「代码 MIT，其余材料 CC BY 4.0」，而我们用的是主客体结构与 ITC 实测表，
属「其余材料」。本仓库的 `docs/pilot-chem.html` 早就写的是 CC BY 4.0，是族实例的许可字段记反了。

**等重跑**：这 25 条要等 11/05–11/08 A1 重跑题库才会进 `docs/data/family-workbench.json` 和每题文件夹。
在那之前 `tests/test_license.py` 里的 `PENDING_RERUN_BLANK` / `PENDING_RERUN_MIT` 列着这些实例号；重跑后这两条测试会变红，删掉清单即可。

## 怎么重跑这份审计

```bash
python tools/export_license_audit.py --print
```

需要本机的论文全文（`inputs/papers/`、`inputs/paper-candidates/`，都不在 Git 上）才能做逐词比对和出版方许可核对。
全文不在本机时，审计会把对应的卡记成 `checked: false` 并写明原因，**不会**把没测过的当成干净的。
