# 许可审计（W2，2026-11-02）

上传 Hugging Face 之前，逐来源核对「我们从它那里发布了什么、它的许可允许什么、许可写在哪」。
数据由 `tools/export_license_audit.py` 生成到 [docs/data/license-audit.json](docs/data/license-audit.json)，
规则由 [tests/test_license.py](tests/test_license.py) 钉住。本页只写审计出来的结论，不替任何来源断定许可。
表格由工具写在标记块之间，页面上的数字不会和 JSON 不一致。

## 结论

<!-- audit-summary:begin -->

| | |
|---|---|
| 来源 | 37 个（336 道在库题 + 1 张已发布但未用的卡） |
| 不可发布 | **0 个** |
| 可直接发布 | 30 个 |
| 上传前要复核 | 6 个（原因见下，都不是阻塞项） |
| 要先做决定的 | **1 个：OE62（CC BY-SA 4.0）** |
| 许可由来源自己确认 | 31 个（出版方本机副本 21 + 来源许可页面 10，2026-11-02 读） |
| 许可只有本项目记录 | 4 个（都不发布它的坐标） |

<!-- audit-summary:end -->

一句话：**没有发现「不能转载却转载了」的来源**；真正要定的只有 OE62 的相同方式共享，以及 16 张证据／设计卡里几处逐词相同的短句要改写。

2026-11-02 补：原来有 8 个数据库／数据集「发布了它的坐标，而许可只有我们自己的记录」。这 8 个（外加 OE62 与 Schäfermeier 2026）的许可页面已逐个读过，原话、网址和日期记在
[docs/data/license-statements.json](docs/data/license-statements.json)，见下面「来源许可页面的原话」一节。**凡是本库发布其坐标的来源，许可现在都由来源自己确认**，不再有只凭本项目记录的。

## 为什么要分三类看

同一批题，从来源拿的东西完全不同，只有第一类才是「转载」问题：

<!-- audit-classes:begin -->

| 类别 | 道数 | 含义 | 许可要求 |
|---|---|---|---|
| 上游坐标 | 239 | 附件里的数字是来源自己的（照抄、对称展开、约简成质心、刚性旋转、转格式） | 必须允许再分发 |
| 本项目坐标 | 55 | 几何是本项目按论文印出的标量（晶格常数、转角、螺距）造的 | 不依赖来源许可 |
| 本项目转述 | 42 | 证据卡／设计卡：本项目转述的事实与数值，每条带原文位置 | 事实不受保护，但句子不能逐词照搬 |

<!-- audit-classes:end -->

## 逐来源

「许可出处」= 谁说的，强到弱三级：

- **出版方副本**：论文本机副本里出版方自己的声明（JATS `<permissions>` 块，或 PDF 上的许可行）。
- **来源许可页面**：来源自己的许可页面，2026-11-02 读过，原话与日期记在 [docs/data/license-statements.json](docs/data/license-statements.json)。页面可以再打开核对。
- **仅本项目记录**：只有我们下载时记下来的那一条（`sources.json` / trace）。现在只剩 4 个来源属这一级，而且都不发布它们的坐标（只用数值与事实），所以不是阻塞项。

<!-- audit-sources:begin -->

| 来源 | 道数 | 发布什么 | 许可 | 许可出处 | 判定 |
|---|---|---|---|---|---|
| RCSB PDB / wwPDB | 99 | 上游坐标 99 | CC0 1.0 | 来源许可页面（2026-11-02 读） | 可发布 |
| Crystallography Open Database | 52 | 上游坐标 52 | 公有领域（COD 贡献者声明） | 来源许可页面（2026-11-02 读） | 可发布 |
| QM7-X（Zenodo 4288677） | 31 | 上游坐标 31 | CC BY 4.0 | 来源许可页面（2026-11-02 读） | 可发布 |
| SAMPL9 挑战赛（samplchallenges/SAMPL9） | 13 | 上游坐标 13 | CC BY 4.0 | 来源许可页面（2026-11-02 读） | 可发布 |
| Cao et al., Nature 556, 43 (2018) / arXiv:1803.02342 | 11 | 本项目坐标 7、本项目转述 4 | arXiv 非独占许可（授权 arXiv 分发，不授权第三方转载） | 仅本项目记录 | 上传前复核 |
| Landscape17（Figshare 29949230） | 11 | 上游坐标 11 | CC BY 4.0 | 来源许可页面（2026-11-02 读） | 可发布 |
| Cottet et al., arXiv:1401.4062 | 10 | 本项目坐标 8、本项目转述 2 | arXiv 非独占许可（授权 arXiv 分发，不授权第三方转载） | 仅本项目记录 | 上传前复核 |
| Hill et al., Nano Lett. 8, 2341 (2008) | 10 | 本项目坐标 10 | 不依赖许可（只用事实数值） | 不依赖 | 可发布 |
| Shaban et al., Materials 17, 5080 (2024) | 10 | 本项目坐标 8、本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| RCSB PDB / wwPDB（DNA 折纸） | 10 | 上游坐标 10 | CC0 1.0 | 来源许可页面（2026-11-02 读） | 可发布 |
| Crystallography Open Database（MOF） | 9 | 上游坐标 9 | 公有领域（COD 贡献者声明） | 来源许可页面（2026-11-02 读） | 可发布 |
| Altun, Bleda & Trindle, Molecules 26, 2623 (2021) | 9 | 上游坐标 5、本项目转述 4 | CC BY 4.0 | 出版方副本 | 可发布 |
| Kerelsky et al., Nature 572, 95 (2019) / arXiv:1812.08776 | 7 | 本项目坐标 3、本项目转述 4 | arXiv 非独占许可（授权 arXiv 分发，不授权第三方转载） | 仅本项目记录 | 上传前复核 |
| Gazmeh et al., Sci. Rep. 15, 38349 (2025) | 7 | 本项目坐标 7 | CC BY-NC-ND 4.0 | 出版方副本 | 可发布 |
| **OE62（TUM mediaTUM 1507656）** | **5** | **上游坐标 5** | **CC BY-SA 4.0** | **来源许可页面（2026-11-02 读）** | **待定** |
| Yu, Qu, Guo & Peng, Chem. Mater. 15, 2854 (2003) | 5 | 本项目坐标 5 | 不依赖许可（只用事实数值） | 不依赖 | 可发布 |
| Fookes, Polo Parada & Fidalgo, Sensors 23, 1433 (2023) | 4 | 本项目坐标 3、本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| RCSB PDB 1AA5 | 4 | 上游坐标 4 | CC0 1.0 | 来源许可页面（2026-11-02 读） | 可发布 |
| Dinç et al., Org. Chem. Front. (2024) | 3 | 本项目坐标 2、本项目转述 1 | CC BY 3.0 | 出版方副本 | 可发布 |
| Jiang et al., Nature 521, 545 (2015) | 3 | 本项目转述 3 | PMC 作者稿（非 CC） | 出版方副本 | 上传前复核 |
| Schäfermeier et al., arXiv:2602.13060 | 3 | 本项目坐标 2、本项目转述 1 | CC BY-NC-ND 4.0 | 来源许可页面（2026-11-02 读） | 可发布 |
| Blom et al., Molecules 21, 16 (2015) | 2 | 本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| Chetry et al., ACS Appl. Mater. Interfaces (2026) | 2 | 本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| Filip et al., Nat. Commun. 5, 5757 (2014) | 2 | 本项目转述 2 | 版权归出版方，保留所有权利 | 出版方副本 | 上传前复核 |
| Rando et al., Chem. Sci. (2025) | 2 | 本项目转述 2 | CC BY 3.0 ← 原记作 CC BY 4.0 | 出版方副本 | 可发布 |
| Vincent et al., Chem. Eur. J. (2025) | 2 | 本项目转述 2 | CC BY 4.0 | 出版方副本 | 可发布 |
| Cuello et al., eLife 6, e28032 (2017) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Della Sala et al., Chem. Sci. 12, 9952 (2021) | 1 | 本项目转述 1 | CC BY 3.0 | 出版方副本 | 可发布 |
| Gómez-González et al., Pharmaceutics 14, 60 (2021) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Ikeda et al., Membranes 11, 627 (2021) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Kaabel et al., Chem. Sci. 8, 2184 (2017) | 1 | 本项目转述 1 | CC BY 3.0 | 出版方副本 | 可发布 |
| Mühlbauer et al., Science 323, 915 (2009) / arXiv:0902.1968 | 1 | 本项目转述 1 | arXiv 非独占许可（授权 arXiv 分发，不授权第三方转载） | 仅本项目记录 | 可发布 |
| Rasmussen et al., Nature 477, 549 (2011) | 1 | 本项目转述 1 | PMC 作者稿（非 CC） | 出版方副本 | 上传前复核 |
| Shuto et al., JACS Au 3, 2905 (2023) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Wilde et al., Sci. Rep. 7, 45941 (2017) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Zhai et al., ACS Cent. Sci. 11, 1753 (2025) | 1 | 本项目转述 1 | CC BY 4.0 | 出版方副本 | 可发布 |
| Kim et al., Int. J. Mol. Sci. 25, 9919 (2024) | 0 | — | CC BY 4.0 | 出版方副本 | 可发布 |

<!-- audit-sources:end -->

**四个 arXiv 预印本（Cao、Kerelsky、Cottet、Mühlbauer）要说清楚一件事**：arXiv 的非独占许可是作者授权 arXiv 分发，
**不是**授权第三方转载。这四篇我们一个字都没转载，依据是「事实与数值不受版权保护」，不是依据许可。表里的许可名只是记录现状。

## 必须做出的决定：OE62

OE62 是 **CC BY-SA 4.0**（相同方式共享），而 QNP023–QNP027 这 5 道发布了它的 `xyz_pbe_relaxed` 坐标原样。
2026-11-02 在 mediaTUM 记录 1507656 的权利栏确认了这一条（原话 `by-sa, http://creativecommons.org/licenses/by-sa/4.0`），所以这不是记录有误，决定必须做。
相同方式共享要求「改编作品以相同许可发布」，这会和整库许可相互作用，所以必须先定，三条路：

| 路 | 做法 | 代价 |
|---|---|---|
| ① 整库 CC BY-SA 4.0 | 最省事，一次定清 | 传染性许可，别人拿去做闭源训练集会犹豫，影响采用 |
| ② 主库 CC BY 4.0 + OE62 单列子集 CC BY-SA 4.0（**建议**） | 5 道单独一个 split，许可写在 split 上 | 要在数据卡里解释两段许可 |
| ③ 撤掉这 5 道 | 一刀两断 | 量子 × 1–10 nm 格从 10 道掉到 5 道，这格本来就是最难填的 |

补充事实：这 5 道全在「量子 × 1–10 nm」格，该格共 10 道（另 5 道是 QND008/009、QNI014/015/016，来自 QM7-X 与 COD，许可无问题）。

## 来源许可页面的原话（2026-11-02 读）

用内置浏览器只读打开各来源自己的许可页面抄录，没有下载任何文件。这一节让「许可出处 = 来源许可页面」的那几行可核对：

<!-- audit-statements:begin -->

| 来源页面 | 覆盖哪些来源 | 看到的原话 | 许可 | 义务 |
|---|---|---|---|---|
| [RCSB PDB 使用政策页](https://www.rcsb.org/pages/usage-policy)（2026-11-02 读） | RCSB PDB / wwPDB；RCSB PDB / wwPDB（DNA 折纸）；RCSB PDB 1AA5 | `The wwPDB policy states that data files contained in the PDB archive are available under the CC0 1.0 Universal (CC0 1.0) Public Domain Dedication.` | CC0 1.0 | 许可本身无强制义务。同页另说：鼓励使用者署名 PDB 结构数据的原作者（encouraged，不是条件）。本库照此在每道题的 attribution 里写原沉积作者与 PDB 编号。 |
| [Crystallography Open Database 首页许可声明](https://www.crystallography.net/cod/)（2026-11-02 读） | Crystallography Open Database；Crystallography Open Database（MOF） | `All data in the COD and the database itself are dedicated to the public domain and licensed under the CC0 License.` | 公有领域（COD 贡献者声明） | 许可本身无强制义务。同句之后另说：使用者应致谢结构数据的原作者（should acknowledge）。COD 的 CIF 文件头同样要求引用原始文献——本库 52 道 COD 题里只有 9 道在许可字段里记了原始文献，其余要在 L1 补齐。 |
| [QM7-X 的 Zenodo 记录（4288677，Version 2.0）](https://zenodo.org/records/4288677)（2026-11-02 读） | QM7-X（Zenodo 4288677） | `Creative Commons Attribution 4.0 International`<br>—— 记录的 Rights / License 字段（Version 2.0，2020-11-23 发布） | CC BY 4.0 | 署名：Hoja, Medrano Sandonas, Ernst, Vazquez-Mayagoitia, DiStasio Jr. & Tkatchenko, Sci. Data 8, 43 (2021)，doi:10.1038/s41597-021-00812-2，并指明本库改了格式（HDF5 → XYZ / JSON，只取坐标与所需标量）。 |
| [SAMPL9 仓库 README 的 LICENSE 节](https://raw.githubusercontent.com/samplchallenges/SAMPL9/master/README.md)（2026-11-02 读） | SAMPL9 挑战赛（samplchallenges/SAMPL9） | `MIT for all software/code / CC-BY 4.0 for all other materials`<br>—— LICENSE 节的两条分项；引语前一句说明这里的材料按情况分别适用 CC-BY 与 MIT 两种许可 | CC BY 4.0 | 署名：SAMPL9 挑战赛（samplchallenges/SAMPL9）与 ITC 实测数据的提供者（WP6 为 Isaacs 组，bCD 为 Gilson 组）；README 另请致谢 NIH R01GM124270（David L. Mobley, UC Irvine）。 |
| [Landscape17 的 Figshare 条目（29949230）](https://figshare.com/articles/dataset/Landscape17/29949230)（2026-11-02 读） | Landscape17（Figshare 29949230） | `CC BY 4.0`<br>—— 条目的 LICENCE 字段（数据集 2025-08-22 发布，Vlad Cărare 等） | CC BY 4.0 | 署名：Cărare, Thiemann, Morrow, Wales, Pyzer-Knapp & Dicks, npj Comput. Mater. (2025)，doi:10.1038/s41524-025-01878-x，数据集 doi:10.6084/m9.figshare.29949230；并指明本库去掉了力列与能量注释，只留坐标。 |
| [OE62 的 TUM mediaTUM 记录（1507656）](https://mediatum.ub.tum.de/1507656)（2026-11-02 读） | OE62（TUM mediaTUM 1507656） | `by-sa, http://creativecommons.org/licenses/by-sa/4.0`<br>—— 记录的 Rechte（权利）字段；记录 2019-07-11 发布，负责人 Oberhofer, Harald | CC BY-SA 4.0 | 署名 + 相同方式共享。署名：Stuke, Kunkel, Golze, Todorović, Margraf, Reuter, Rinke & Oberhofer，doi:10.14459/2019mp1507656，论文 doi:10.1038/s41597-020-0385-y。 |
| [arXiv:2602.13060 摘要页的权利栏](https://arxiv.org/abs/2602.13060)（2026-11-02 读） | Schäfermeier et al., arXiv:2602.13060 | `http://creativecommons.org/licenses/by-nc-nd/4.0/`<br>—— 摘要页 “Rights to this article” 一栏的许可链接与图标（页面上只有图标和 view license 两个字，许可由链接本身给出） | CC BY-NC-ND 4.0 | 署名 + 不得改编 + 非商业。本库只用该文的数值（涡旋点阵常数等），不转载文字与图，因此这些限制不影响发布；记录在案是为了别人不会误以为可以再分发原文。 |

<!-- audit-statements:end -->

| 读不到的页面 | 怎么处理 |
|---|---|
| `https://www.wwpdb.org/about/usage-policies` | 本会话的浏览器打不开该站（导航被拒绝）。改以 RCSB 使用政策页为证——该页正是转述 wwPDB 政策，两处同指 CC0 1.0。要一手页面就自己打开一次。 |

## 上传前的核对清单

1. ~~**8 个数据库／数据集的许可，只有我们自己的记录**（PDB×3、COD×2、QM7-X、OE62、Landscape17、SAMPL9）。~~
   **2026-11-02 做完**：10 个来源的许可页面逐个读过（上面那 8 个 + OE62 + Schäfermeier 2026），
   原话、网址、日期记进 [docs/data/license-statements.json](docs/data/license-statements.json)
   与各自的 `sources.json`。有一页打不开：`https://www.wwpdb.org/about/usage-policies`
   （本会话的浏览器被拒），wwPDB 的原话改以 RCSB 使用政策页为证——该页正是转述 wwPDB 政策，两处同指 CC0 1.0。
2. **Rando 2025 的许可对不上**：仓库记作 CC BY 4.0，论文自带的 JATS 许可块写的是 CC BY 3.0。以出版方页面为准，确认后统一改
   （`docs/assets/families/design/sources.json`、三份卡片、`templates/family-manifest.json`）。
   这一条没有在 11-02 一并处理：两个版本都允许再分发，差别只在署名条款的措辞，要选哪个是人的判断，不该由工具替你定。
3. ~~**Schäfermeier 2026 的 CC BY-NC-ND 无法本机核对**（arXiv PDF 里没有许可行）。~~
   **2026-11-02 做完**：arXiv:2602.13060 摘要页的权利栏确认是 CC BY-NC-ND 4.0。我们只用该文数值，不受影响。
4. **COD 的引用要求**：COD 文件头要求引用原始文献，52 道里只有 9 道在许可字段记了原始文献。数据卡里要么逐条补，要么统一说明。
   COD 首页的说法是「使用者应致谢结构数据的原作者」（should acknowledge），不是许可条件，但要做。
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

SAMPL9 的 MIT 是错的：其 README 的 LICENSE 节写明「代码 MIT，其余材料 CC BY 4.0」（2026-11-02 读到的原话见上节），
而我们用的是主客体结构与 ITC 实测表，属「其余材料」。本仓库的 `docs/pilot-chem.html` 早就写的是 CC BY 4.0，
是族实例的许可字段记反了。同一批里还有 5 条来源说明写着「SAMPL9 host-guest challenge (MIT License)」，也一并改了。

**另外新增（不等重跑，立即生效）**：10 个来源的许可页面原话记进
[docs/data/license-statements.json](docs/data/license-statements.json)，并在各自的 `sources.json` 里重复一份：
`families/assemblies`、`bio`、`materials/sources-cod-2026-10-03`、`materials/sources-noncubic`、`families/molecules`、
`families/reaction`、`families/vortex` 七个已有文件加 `license_statement` 段，另新建
`families/hostguest/sources.json`（SAMPL9）、`families/conformers/sources.json`（QM7-X）、
`qa/sources-oe62.json`（OE62）——后三处的附件本身进了题库哈希不能改，所以许可记录单独放在旁边。
副作用（无害）：`tools/export_qa_folders.py` 会给 SAMPL9 与 QM7-X 的题填上 `asset_record`（原来是 `null`），所以下一次重导每题文件夹时这些 `info.json` 会多一个字段。

**等重跑**：这 25 条要等 11/05–11/08 A1 重跑题库才会进 `docs/data/family-workbench.json` 和每题文件夹。
在那之前 `tests/test_license.py` 里的 `PENDING_RERUN_BLANK` / `PENDING_RERUN_MIT` 列着这些实例号；重跑后这两条测试会变红，删掉清单即可。

## 怎么重跑这份审计

```bash
python tools/export_license_audit.py --print
```

需要本机的论文全文（`inputs/papers/`、`inputs/paper-candidates/`，都不在 Git 上）才能做逐词比对和出版方许可核对。
全文不在本机时，审计会把对应的卡记成 `checked: false` 并写明原因，**不会**把没测过的当成干净的。

来源许可页面那一级不联网：工具只读 `docs/data/license-statements.json` 里已抄下的原话。要重新核对页面，
自己打开那些网址看一遍，然后改这个文件——改完 `tests/test_license.py` 会要求各 `sources.json` 里的副本逐字跟上。
