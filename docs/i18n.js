/* English chrome for the atlas, with a 中文 switch.

   The advisor asked for the site in English (2026-11-03: "中文肯定是不 ready 的"). The question data itself is
   generated -- its Chinese explanatory fields come out of task_families/ and tools/export_*.py and have to be
   translated there, which is a separate pass. This file translates what the page itself says: navigation,
   headings, captions, filters, table headers and the sentences the scripts build. It matches whole strings, so
   a question title or an option value is never touched. Default is English; the choice is remembered. */
(() => {
  const DICT = {
    // header and navigation
    '概览': 'Overview', '问题池': 'Question pool', '题目卡片': 'Question cards', '子领域': 'Subdomains',
    '分类与方法': 'Taxonomy & method', '出题系统': 'Generation system', '题型': 'Task families', '审核': 'Review',
    // 2026-11-04: 分类与方法 / 出题系统 / 审核 合成一页后的新词
    '方法与审核': 'Method & review', '审核队列': 'Review queue', '题型 ↗': 'Task families ↗',
    '方法与审核 · GeoBench': 'Method & review · GeoBench',
    '审核体系 · GeoBench': 'Review system · GeoBench',
    '审核队列 · GeoBench': 'Review queue · GeoBench',
    '本页分区': 'Sections on this page',
    '这一节已经并进「方法与审核」。': 'This section has moved into Method & review.',
    '打开「方法与审核」↗': 'Open Method & review ↗',
    '这个地址保留着，旧链接仍然有效。': 'This address is kept, so older links still work.',
    'GeoBench 首页': 'GeoBench home', '主导航': 'Main navigation',
    // hero
    '从几何理解，': 'From geometry,', '走向科学推理。': 'to scientific reasoning.',
    '面向 LLM / VLM 的分子几何评测研究。': 'A benchmark study of molecular geometry for LLMs and VLMs.',
    '将科学问题、真实结构与可验证的答案，放在同一张地图上。':
      'Scientific questions, real structures and checkable answers on one map.',
    '探索问题池': 'Explore the question pool', '了解研究框架 →': 'How it is built →',
    '01 感知': '01 Perception', '02 推断': '02 Inference', '03 生成 / 设计': '03 Generation / design',
    '感知、推断与设计三个能力层级的示意图': 'The three ability levels: perception, inference, design',
    '抽象结构示意，不代表真实分子': 'Abstract sketch; not a real molecule',
    // top links
    '出题系统：题型族与独立检查器，每一步的代码、保证与局限 ↗':
      'Generation system: task families and independent checkers, with the code, guarantees and limits of each step ↗',
    '题型工作台（每道题的题干、附件、选项、答案与独立检查）↗':
      'Task-family workbench (stem, attachments, options, answer and independent check of every question) ↗',
    '题型覆盖总表 ↗': 'Task-family coverage table ↗', '审核体系 L1–L3 ↗': 'Review system L1–L3 ↗',
    '审核体系 ↗': 'Review system ↗', '统一标准 ↗': 'Shared standard ↗', '旭日图 ↗': 'Sunburst ↗',
    '旭日图与二级子领域 ↗': 'Sunburst and level-2 subdomains ↗', '坐标定义 ↗': 'How the axes are defined ↗',
    '完成数／缺口／人工审核 ↗': 'Done / gaps / human review ↗', '历史存档 ↗': 'Archive ↗',
    '提出建议 ↗': 'Open an issue ↗', '逐来源许可审计 ↗': 'Per-source licence audit ↗',
    // stat line
    '研究资源': 'Sources', '构题来源与评估参考': 'Question sources and evaluation references',
    '当前原型候选': 'Current candidates', '新版初筛通过，待独立审核': 'Passed automated screening, awaiting review',
    '待人工审核': 'Awaiting human review', '完整材料可直接审阅': 'Complete material, ready to read',
    '正式可用题目': 'Formally approved', '保持清晰的质量边界': 'Keeping the quality line explicit',
    // coverage maps
    '四个领域 × 四个尺度（总览）。': 'Four domains × four scales (overview).',
    '4 个领域 × 4 个尺度': '4 domains × 4 scales', '领域 / 推理尺度 →': 'Domain / reasoning scale →',
    '细到子领域的坐标系。': 'The coordinate system, down to subdomains.',
    '能力': 'Ability', '全部能力': 'All abilities', '感知': 'Perception', '推断': 'Inference',
    '生成 / 设计': 'Generation / design', '● 感知': '● Perception', '● 推断': '● Inference',
    '● 生成 / 设计': '● Generation / design', '查看题目 →': 'See the questions →', '尚无题目': 'none yet',
    '缺': 'gap', '量子 / 电子结构': 'Quantum / electronic structure', '化学': 'Chemistry', '材料': 'Materials',
    '生物': 'Biology', '物理（原“量子”）': 'Physics (formerly "quantum")',
    '这个尺度上没有这个子领域的题可做': 'No question of this subdomain exists at this scale',
    '每格左上角是题数，下面是 感知·推断·设计 的拆分。「缺」= 这个像素有意义但还没有题（教授看的就是这 20 格）；「·」= 这个子领域在这个尺度上没有题可做，不算缺口。所有题都已通过程序核验与独立检查器，仍待人工审核。':
      'Each cell shows the number of questions and, below it, the perception·inference·design split. "gap" = the pixel is meaningful but still empty; "·" = no question of this subdomain is possible at this scale, so it is not a gap. Every question passed the generator checks and the independent checker; none has been reviewed by a person yet.',
    // the 32 level-1 subdomains of the detailed map (names only; the data behind them is generated)
    '超导': 'Superconductivity', '磁性': 'Magnetism', '二维材料与莫尔物理': '2D materials & moiré physics',
    '纳米与介观物理': 'Nanoscale & mesoscopic physics', '原子与分子物理': 'Atomic & molecular physics',
    '光子学': 'Photonics', '软物质与生物物理': 'Soft matter & biophysics',
    '有机化学': 'Organic chemistry', '物理与量子化学': 'Physical & quantum chemistry',
    '无机与配位化学': 'Inorganic & coordination chemistry', '超分子化学': 'Supramolecular chemistry',
    '反应与催化': 'Reactions & catalysis', '高分子化学': 'Polymer chemistry',
    '化学生物学与 DNA 纳米技术': 'Chemical biology & DNA nanotechnology',
    '液晶与胶体化学': 'Liquid crystals & colloids',
    '金属与合金': 'Metals & alloys', '陶瓷与氧化物': 'Ceramics & oxides', '半导体': 'Semiconductors',
    '多孔与框架材料': 'Porous & framework materials', '有机与高分子材料': 'Organic & polymer materials',
    '纳米材料与组装': 'Nanomaterials & assembly', '表面与界面': 'Surfaces & interfaces',
    '生物与仿生材料': 'Biological & biomimetic materials',
    '酶': 'Enzymes', '小型与调控蛋白': 'Small & regulatory proteins', '转运与储存蛋白': 'Transport & storage proteins',
    '膜蛋白': 'Membrane proteins', '毒素': 'Toxins', '病毒蛋白与衣壳': 'Viral proteins & capsids',
    '核酸与核蛋白': 'Nucleic acids & nucleoproteins', '大分子机器': 'Macromolecular machines',
    '免疫与识别': 'Immunity & recognition',
    // research path
    '每道题，都能找到来处。': 'Every question can be traced back.',
    '找到科学问题': 'Find the science',
    '论文、数据库与既有 benchmark。每道题都带着自己的来源、原文位置与许可。':
      'Papers, databases and existing benchmarks. Every question carries its source, its locator in that source, and its licence.',
    '看题目的来源 ↗': 'See where questions come from ↗', '定义可验证的任务': 'Define a checkable task',
    '将题型与实例分开，记录输入、答案构建方法及材料缺口。':
      'Task families and instances are kept apart, with inputs, answer construction and missing material recorded.',
    '查看候选 ↗': 'Browse candidates ↗', '让答案有依据': 'Give the answer evidence',
    '通过经过检查的程序取得答案，保留条件与来源，明确审核边界。':
      'Answers come from checked code; conditions and sources are kept, and the limits of review are stated.',
    '理解方法 ↗': 'Read the method ↗',
    // question pool
    '把问题，逐一说清楚。': 'One question at a time, stated in full.',
    '这里只展示材料齐全、通过当前初筛的完整候选题；均待独立人工审核。':
      'Only complete candidates that passed the current screening are shown; all still await independent human review.',
    '搜索问题': 'Search', '编号、题目或论文': 'id, title or paper', '领域': 'Domain', '全部领域': 'All domains',
    '推理尺度': 'Reasoning scale', '全部尺度': 'All scales', '审核状态': 'Status', '全部状态': 'All statuses',
    '有数值答案': 'Has a numeric answer', '重置': 'Reset', '导出当前目录 ↓': 'Export this list ↓',
    '编号 / 题目': 'Id / title', '来源': 'Source', '状态': 'Status', '详情': 'Details',
    '感知 Perception': 'Perception', '推断 Inference': 'Inference',
    '这个区域还没有候选问题。': 'No candidate questions in this area yet.',
    '这是当前研究覆盖的空白，不代表该领域不存在有价值的任务。':
      'That is a gap in what this project covers, not a claim that the area holds no worthwhile task.',
    '清除筛选 →': 'Clear filters →',
    // method
    '分类可以迭代，': 'A taxonomy can change;', '依据必须保留。': 'the evidence has to stay.',
    '分类 v0.1 · 工作定义，尚未形成统一的领域边界与尺寸测量协议。':
      'Taxonomy v0.1 · working definitions; domain boundaries and a size-measurement protocol are not settled.',
    '01 尺度': '01 Scale', '02 学科': '02 Domain', '03 能力': '03 Ability', '04 构建与审核': '04 Build & review',
    '公开展示范围': 'What this site publishes',
    '本站公开资源元数据与当前完整候选题。完整论文、内部证据包与批量答案不随网站发布。':
      'Source metadata and the current complete candidates. Full papers, internal evidence bundles and bulk answer keys are not published here.',
    '目录暂时无法载入': 'The catalog could not be loaded',
    '请刷新页面重试，或前往 GitHub 查看资源。': 'Reload the page, or read the data on GitHub.',
    '关闭详情': 'Close',
    '题库数据以 CC BY 4.0 发布，题内另有说明的除外（逐题的来源、原文位置与许可写在每道题的详情与题目文件夹 info.json 里）。':
      'Question data is released under CC BY 4.0 unless a question says otherwise; each question carries its own source, locator and licence in its detail panel and in its folder’s info.json.',
    // headings of the other pages (their body text is still Chinese; the generated fields need a pass in the generators)
    '题型与计算器 · GeoBench': 'Task families & calculator · GeoBench',
    '一个题型，多份结构，同一套验证。': 'One task family, many structures, one set of checks.',
    '题型覆盖总表': 'Task-family coverage table',
    '题型工作台：看一次完整的构造与验证': 'Workbench: one question built and checked end to end',
    '答案怎么设计：四个选项，唯一正确。': 'How answers are designed: four options, exactly one right.',
    '历史试跑：最大间距与回转半径（v0.1）': 'Historic pilots: maximum extent and radius of gyration (v0.1)',
    '题型决定规则': 'The family fixes the rules',
    '换结构，算答案': 'Swap the structure, compute the answer',
    '全量计算，分层抽查': 'Compute everything, sample for review',
    '160 道原型：缺口与出题路线': 'The 160-question prototype: gaps and routes',
    '被测模型看到什么': 'What the model under test sees',
    '审核侧（含答案）': 'Reviewer side (answer included)',
    '独立检查器：换一套代码再算一遍': 'Independent checker: a second implementation recomputes it',
    'v0.1 数值试跑': 'v0.1 numeric pilots',
    '学生看到什么': 'What the solver sees',
    '代码计算与评分': 'Computation and scoring',
    'v0.1 四选一版本': 'v0.1 four-option version',
    '模型作答区': 'Model answer area',
    '审核与检查记录': 'Review and check records',
    '子领域 · GeoBench': 'Subdomains · GeoBench',
    '子领域：每道题落在哪一格。': 'Subdomains: which cell each question falls in.',
    '表格视图': 'Table view',
    '题目卡片 · GeoBench': 'Question cards · GeoBench',
    '审核体系 L1–L3 — GeoBench': 'Review system L1–L3 — GeoBench',
    '审核体系：题型审定、检查器审阅、分层抽查': 'Review system: family sign-off, checker review, stratified sampling',
    '流程': 'Process',
    '审核表（Excel）': 'Review sheet (Excel)',
    '160 道原型挑选（提议，待教授确认）': 'The 160-question selection (proposed, pending the advisor)',
    'L3 固定四问': 'The four fixed L3 questions',
    'L1 / L2 待审单元': 'L1 / L2 units awaiting review',
    '下一批 L3 抽样计划': 'Next L3 sampling plan',
    '一个题型，': 'One task family,', '多份结构，同一套验证。': 'many structures, one set of checks.',
    '筛查清单': 'Screening list', '题型总表': 'Family table', '题型工作台': 'Workbench',
    '下一批 L3 抽样计划（l3-batch-001）': 'Next L3 sampling plan (l3-batch-001)',

    // 方法与审核 (2026-11-04). These three pages had never been through the English pass; the
    // merge put them behind a top-level entry, which is how it showed. Terms follow what the
    // repository already uses: task family, independent checker, student packet, answer key,
    // reasoning scale, distractor, cell, family sign-off, checker review, stratified sampling.
    '01 / 两种尺度，分别记录': '01 / Two scales, recorded separately',
    '输入尺度描述模型看到的对象；推理尺度描述解题需要关注的范围。例如，输入完整蛋白质而只分析一个原子接触，两者不能混为一谈。':
      'Input scale describes the object the model is shown; reasoning scale describes the range the question actually turns on. A whole protein given as input with a single atomic contact to analyse is not the same number.',
    '主图默认按解题推理尺度分为0.1–1、1–10、10–100和100–1000 nm，保留输入尺度切换。尺寸及测量定义见每道题。':
      'The main map is binned by reasoning scale into 0.1–1, 1–10, 10–100 and 100–1000 nm, with an input-scale view kept alongside. Each question states its sizes and how they were measured.',
    '02 / 学科是层级，不是四个互斥标签': '02 / Disciplines are a hierarchy, not four exclusive labels',
    '电子结构 · 原子力 · 振动与势能曲率': 'Electronic structure · atomic forces · vibrations and curvature of the potential',
    '立体化学 · 构象分析 · 结构与性质': 'Stereochemistry · conformational analysis · structure and property',
    '晶体与缺陷 · 聚合物 · 凝聚态结构': 'Crystals and defects · polymers · condensed-matter structure',
    '结构生物学 · 生物分子识别 · 多分子复合物': 'Structural biology · biomolecular recognition · multi-molecule complexes',
    '子领域细分草案 v0.2：领域 → 第一层 → 叶子，可缩放旭日图 ↗':
      'Subdomain draft v0.2: domain → first level → leaf, as a zoomable sunburst ↗',
    '以上为工作分类示例。允许跨领域标签，按具体问题归类，不因论文使用 DFT 或研究药物就直接决定领域。':
      'These are working examples. Cross-domain labels are allowed: a question is filed by what it asks, not by whether its paper used DFT or studied a drug.',
    '03 / 从感知到设计': '03 / From perception to design',
    '从结构中识别、测量或比较几何关系。': 'Identify, measure or compare a geometric relation in a structure.',
    '在明确条件下，联系几何与物理后果；单纯数值比较不自动成为物理推断。':
      'Under stated conditions, connect geometry to a physical consequence; comparing two numbers is not by itself a physical inference.',
    '提出满足约束的结构；结构操作、有效性与目标性质达成需要分别评分。':
      'Propose a structure that meets the constraints; the edit, its validity and whether the target property is reached are scored separately.',
    '04 / 模型设计题型，程序构建实例': '04 / Models design the task family, code builds the instances',
    '来源整理 → 题型设计 → 输入与答案规则 → 检查通用构建程序 → 批量实例化 → 自动检查与人工抽审。':
      'Sources collected → task family designed → input and answer rules → the shared builder is reviewed → instances generated in batches → automatic checks and human spot-checks.',
    '当前题目从真实结构与性质数据构建。完整题干、输入附件、答案和评分依据齐全，并通过初筛后，才能进入当前题库。程序检查只验证指定量，不证明领域正确性或题目难度；待审核与正式可用之间保持明确区别。':
      'Questions are built from real structures and measured properties. One enters the bank only with a complete stem, its input attachments, an answer and the basis for scoring, and after passing automated screening. The programmatic checks verify the stated quantity only; they do not establish scientific correctness or difficulty. Awaiting review and formally approved are kept apart.',
    '代码出题，独立复算，': 'Code generates. A separate checker',
    '人审代码。': 'recomputes. People review the code.',
    '每个题型是一段确定性代码，批量生成题目；另一段不共享任何代码的检查器从题干重新计算每道题。':
      'A task family is one piece of deterministic code that generates questions in batches; a checker that shares no code with it recomputes every question from the stem.',
    '代码经人审定后，同一题型的所有题都可复现、可核对。出题全程不调用任何模型。':
      'Once the code is signed off, every question of that family is reproducible and checkable. No model is called anywhere in generation.',
    '题型族': 'Task families',
    '读取中…': 'Loading…',
    '九条质量原则': 'Nine quality principles',
    '原则全文与命令见仓库': 'Full principles and commands are in the repository',
    '。旧的逐题 AI 流程（': '. The older per-question AI pipeline (',
    '）已归档，只用于追溯旧运行；M0–M6 仍作为阶段名称对照。':
      ') is archived and kept only to trace old runs; M0–M6 remain as stage names for reference.',
    '从来源到正式题：五个阶段，十二步': 'From source to approved question: five stages, twelve steps',
    '每一步做什么、保证什么': 'What each step does and what it guarantees',
    '选择一步，查看输入输出、保证、局限、命令与代码。':
      'Pick a step to see its inputs and outputs, guarantees, limits, command and code.',
    '题型族目录': 'Task-family catalogue',
    '数据路线': 'Data route',
    '实例': 'Instances',
    '覆盖格': 'Cells covered',
    '独立检查方法': 'Independent check',
    '独立性与可复现': 'Independence and reproducibility',
    '扩展能力：枚举器探针': 'Capacity: the enumerator probe',
    '结构': 'Structures',
    '候选': 'Candidates',
    '抽样': 'Sampled',
    '题型接受': 'Accepted by the family',
    '独立检查通过': 'Passed the independent check',
    '估计可出': 'Estimated yield',
    '探针发现并修正的问题': 'What the probe found and what was fixed',
    '第一次探针（runs/enum-v01、v02）显示 FRET 效率题在大量实例上“正确项总是最大”：当 E > 0.5 时，登记的错误机制全部给出更小的值。只看原来 3 道题时这个问题看不出来。修正方法是给题型族加一种给出更大值的真实错误（用最近重原子对代替标记原子），并允许从题设 R0 列表中选取使目标秩可达的值。修正后答案位置均衡，已有 3 道题按新版本重新生成（v19）。':
      'The first probe (runs/enum-v01, v02) showed that across many instances of the FRET-efficiency family the correct option was always the largest: above E > 0.5 every registered mistake gives a smaller value. With only the original 3 questions the pattern was invisible. The fix adds a real mistake that gives a larger value (the nearest heavy-atom pair in place of the labelled atoms) and lets R0 be taken from the list in the stem so the target rank is reachable. Answer positions are balanced after the fix, and the 3 existing questions were regenerated (v19).',
    '批量选题规则与差距（暂定）': 'Batch selection rules and gaps (provisional)',
    '每格：能选多少、还差什么': 'Per cell: how many are selectable, and what is missing',
    '每格显示“在全部上限下最多能选 / 目标”；绿色条为最多可选，金色条为同时满足能力比例时的可选。点击格子查看缺口。':
      'Each cell shows "the most selectable under all caps / target". The green bar is that maximum; the gold bar is what stays selectable while the ability proportions are also met. Click a cell for its gap.',
    '规则': 'Rules',
    '待导师确认': 'Awaiting the advisor\'s confirmation',
    '如何复现': 'How to reproduce',
    '以下命令在仓库根目录运行，不需要任何 API Key。生成与复核都是确定性的：同样的代码和规格得到逐字节相同的结果。':
      'Run these from the repository root; no API key is needed. Generation and re-checking are deterministic: the same code and the same spec give byte-identical results.',
    '未能加载 data/system.json，请通过 HTTP 服务打开并刷新。':
      'Could not load data/system.json. Open the page over HTTP and refresh.',
    '加载中…': 'Loading…',
    'GeoBench · 出题系统': 'GeoBench · Generation system',
    '层级': 'Level',
    '频率': 'Frequency',
    '做什么': 'What it does',
    'L0 自动核验': 'L0 Automatic verification',
    '每个实例': 'Every instance',
    '独立检查器重算、四项唯一、答案键一致、无泄漏、来源哈希':
      'Independent checker recomputes; four distinct options; answer key agrees; no leakage; source hashes',
    '已运行': 'Running',
    'L1 题型审定': 'L1 Family sign-off',
    '每个题型一次': 'Once per task family',
    '人工读题型卡片（考点、题干、物理条件、干扰机制、限制）与两个样例，结论为通过或修改；记录绑定生成代码与注册表行的哈希，任一改变即失效':
      'A person reads the family card (what it tests, the stem, the physical conditions, the distractor mechanisms, the limits) and two samples, and records pass or revise. The record is bound to hashes of the generating code and its registry row; a change to either voids it',
    '工具已建，未运行': 'Tooling built, not yet run',
    'L2 检查器审阅': 'L2 Checker review',
    '人工读独立检查器代码（可附一次模型代码审阅）；记录绑定检查器代码哈希':
      'A person reads the independent checker\'s code (a model code review may be attached); the record is bound to the checker\'s code hash',
    'L3 分层抽查': 'L3 Stratified sampling',
    '每批': 'Every batch',
    '按 题型 × 来源 × 尺度格 分层；新题型或新来源首批全检，稳定后每层 max(2, 10%)；轻量模型答固定四问，被标记的全部转人工，另抽模型判“通过”的题给人工校准':
      'Stratified by task family × source × scale cell. The first batch of a new family or source is checked in full; once it is stable, max(2, 10%) per stratum. A light model answers four fixed questions; everything it flags goes to a person, and some it passed are sampled too, to calibrate',
    'L4 难度测试': 'L4 Difficulty measurement',
    '每批（不属于审核）': 'Every batch (not part of review)',
    '模型实际作答学生包，得到正确率': 'Models answer the student packets and a score comes out',
    '未建（用户决定暂缓）': 'Not built (deferred)',
    '实例状态：生成 → L0（可暂计配额）→ L1 + L2（题型已审定）→ L3 抽查通过 → 正式计入。抽查不合格：改题型模板，整个题型重新生成一批，不逐题手工修补。':
      'Instance states: generated → L0 (may count provisionally) → L1 + L2 (family signed off) → passed L3 → formally counted. When a spot-check fails, the family template is changed and the whole family is regenerated; questions are not patched one at a time.',
    'L1 / L2 可以离线审：': 'L1 and L2 can be reviewed offline:',
    '下载审核表': 'download the review sheet',
    '，每个审核单元一行，含题型卡片、两个样例、代码链接，只填黄色四列（决定、审核人姓名、日期、意见）。交回后运行':
      ' — one row per review unit, with the family card, two samples and links to the code. Fill in the four yellow columns only (decision, reviewer name, date, comment). When it comes back, run',
    'python tools/review_sheet.py import --file 文件名.xlsx --dry-run':
      'python tools/review_sheet.py import --file yourfile.xlsx --dry-run',
    '检查，再去掉 --dry-run 写入。导入会核对每行的绑定哈希：导出后代码或注册表改过的行会被拒收，需要重新导出；审核人必须是作出判断的本人，AI 助手不能代填。':
      'to check it, then drop --dry-run to write. The import verifies each row\'s bound hash: a row whose code or registry entry changed after export is refused and has to be exported again. The reviewer must be the person who made the judgement; an AI assistant may not fill it in for them.',
    '格': 'Cells',
    '感知 / 推断 / 设计': 'Perception / inference / design',
    '选中（* 待教授决定类别；† 旧模板题；‡ 旧题的四选一版本）':
      'Selected (* category awaiting the advisor; † old-template question; ‡ four-option version of an old question)',
    '备用': 'Spare',
    '说明': 'Notes',
    '全部': 'All',
    '旧模板': 'Old template',
    '单元': 'Unit',
    '检查器': 'Checker',
    '层（单元 | 来源 | 尺度格）': 'Stratum (unit | source | scale cell)',
    '层内': 'In stratum',
    '抽取': 'To sample',
    '抽中': 'Sampled',
    '未能加载 data/review-queue.json，请通过 HTTP 服务打开并刷新。':
      'Could not load data/review-queue.json. Open the page over HTTP and refresh.',
    '2026-09-22 专项筛查：42 保留待审 · 32 小修 · 6 重构 ↗':
      '2026-09-22 targeted screening: 42 kept for review · 32 minor fixes · 6 rebuilt ↗',
    '· 原 80 道均保留，待修项暂停当前配额。': '· All 80 were kept; those awaiting fixes are held out of the current quota.',
    '完整题目，才进入审核队列。': 'Only complete questions enter the review queue.',
    '任务方向是研究规划；候选题需要实际材料、可作答题干、答案与评分依据。通过辅助初筛后，仍须独立人工审核。':
      'A task direction is research planning. A candidate question needs real material, an answerable stem, an answer and a basis for scoring. Passing the assisted screening does not replace independent human review.',
    '人工审核队列': 'Human review queue',
    '材料批次：原批次 10 道（当前以复查为准） · 材料 × 0.1–1 nm ↗':
      'Materials batch: 10 in the original batch (the re-check governs) · materials × 0.1–1 nm ↗',
    '材料 1–10nm 批次：原批次 10 道（当前以复查为准） · 材料 × 1–10 nm ↗':
      'Materials 1–10 nm batch: 10 in the original batch (the re-check governs) · materials × 1–10 nm ↗',
    '生物批次：两格已各补满 10/10 · 生物 × 0.1–1 nm 与 1–10 nm ↗':
      'Biology batch: both cells filled to 10/10 · biology × 0.1–1 nm and 1–10 nm ↗',
    '化学批次：原批次 10 道（当前以复查为准） · 化学 × 0.1–1 nm ↗':
      'Chemistry batch: 10 in the original batch (the re-check governs) · chemistry × 0.1–1 nm ↗',
    '化学 1–10nm 批次：原批次 10 道（当前以复查为准） · 化学 × 1–10 nm ↗':
      'Chemistry 1–10 nm batch: 10 in the original batch (the re-check governs) · chemistry × 1–10 nm ↗',
    '量子批次：原批次 10 道（当前以复查为准） · 量子 × 0.1–1 nm ↗':
      'Quantum batch: 10 in the original batch (the re-check governs) · quantum × 0.1–1 nm ↗',
    '量子 1–10nm 批次：原批次 10 道（当前以复查为准） · 量子 × 1–10 nm ↗':
      'Quantum 1–10 nm batch: 10 in the original batch (the re-check governs) · quantum × 1–10 nm ↗',
    '上一批论文构题：4道新增候选与6项暂缓原因 ↗': 'Last paper-sourced batch: 4 new candidates, and why 6 were deferred ↗',
    '这些题可以直接审阅完整材料。审核重点包括科学意义、几何是否必要、答案适用条件、评分可执行性和难度。当前没有专家审核通过的记录。':
      'These can be reviewed with their full material in hand. What matters: scientific meaning, whether the geometry is necessary, the conditions under which the answer holds, whether the scoring can be carried out, and difficulty. No expert sign-off has been recorded yet.',
    'Q02：从方向到完整实例': 'Q02: from a direction to a complete instance',
    'Q02“力与位移”是方向编号；QNP001 是该方向下第一个完整题目，使用 QM7-X 官方 8000 分片中的分子 7001，匹配 c1-opt 与 c1-d1，包含全部 14 个原子的 A/B 坐标和 B 处原子力。':
      'Q02 "force and displacement" is a direction number; QNP001 is the first complete question under it. It uses molecule 7001 from the official QM7-X 8000 shard, matching c1-opt with c1-d1, and carries the A and B coordinates of all 14 atoms together with the atomic forces at B.',
    '2026-09-21 更新：': '2026-09-21 update:',
    '量子 × 0.1–1 nm 已在 q02-force-v04-002（见': 'quantum × 0.1–1 nm was filled by q02-force-v04-002 (see',
    '量子批次页 ↗': 'the quantum batch page ↗',
    '）补满到': ') to',
    '，新增 5 个不同分子（7002/7035/7040/7070/7122）共 9 道候选：5 道感知改用通用 xyz_distance/xyz_angle 数值验证器，4 道推断延续下方方法并新增偶极矩变化任务。以下 QNP001 原有记录未改写。':
      ', with 5 further molecules (7002/7035/7040/7070/7122) giving 9 candidates: 5 perception questions now use the generic xyz_distance / xyz_angle numeric verifier, and 4 inference questions follow the method below with a new dipole-change task. The original QNP001 record below is unchanged.',
    '打开 QNP001 完整题目 →': 'Open the full QNP001 question →',
    '查看 M0–M6 输入输出 ↗': 'See the M0–M6 inputs and outputs ↗',
    '结果：力与指定形变的点积约 −1.8479 eV，表示 B 处瞬时力投影反对沿该方向继续形变。它不是有限能量差，也不能证明 A 是稳定极小值。输入和推理范围均约 0.694 nm，属于量子 × 0.1–1 nm。':
      'Result: the dot product of the force with the given displacement is about −1.8479 eV, meaning the instantaneous force at B opposes further displacement along that direction. It is not a finite energy difference, and it does not establish that A is a stable minimum. Input and reasoning both span about 0.694 nm, so this is quantum × 0.1–1 nm.',
    '数值由补充计算器计算，并用 Decimal 算术复核；当前通用流程走 evidence_review，解释部分仍需人工语义审核。没有将补充计算器冒称为已接入的通用自动评分器。':
      'The numbers come from a supplementary calculator and were re-checked in Decimal arithmetic; the general pipeline currently routes this through evidence_review, and the explanation still needs a person to read it. The supplementary calculator is not presented as a general automatic grader already wired in.',
    'QM7-X 官方来源与数据许可 ↗': 'QM7-X: official source and data licence ↗',
    '补充计算器代码 ↗': 'Supplementary calculator code ↗',
    '16 个格子的当前缺口': 'Current gaps across the 16 cells',
    '按解题推理尺度，每格目标 10 道。感知、推断、设计各约 3 道是软目标；所有数字来自当前目录，不把规划方向和历史归档算作完成题。':
      'Binned by reasoning scale, the target is 10 per cell. About 3 each of perception, inference and design is a soft target. Every number comes from the current catalogue; planned directions and archived material are not counted as finished questions.',
    '初筛／目标': 'Screened / target',
    '感知／推断／设计': 'Perception / inference / design',
    '初筛缺口': 'Screening gap',
    '当前完整候选：准入检查': 'Current complete candidates: the admission check',
    '检查完整题干、实际附件、答案与评分、来源与考点、两种实测尺度、初筛记录及是否属于当前原型。未满足的条目先补材料或重构，不混入人工审核队列。这是材料和状态检查，不替代科学内容复审。':
      'It checks for a complete stem, the actual attachments, an answer and its scoring, the source and what the question tests, both measured scales, the screening record, and whether it belongs to the current prototype. Anything that fails is completed or rebuilt first rather than joining the human review queue. This checks material and state; it does not replace review of the science.',
    '旧题与规划方向历史存档 ↗': 'Archive of old questions and planned directions ↗',
    '统计载入失败，请刷新或下载检查记录。': 'The statistics could not be loaded. Refresh, or download the check record.',
    '查看统一标准、16格缺口与人工审核队列 ↗': 'See the shared standard, the 16-cell gaps and the human review queue ↗',
    '问题在哪里，空白在哪里。': 'Where the questions are, and where the blanks are.',
    '科学领域 × 输入对象尺度': 'Scientific domain × input object scale',
    '只展示当前完整候选，按实际推理尺度统计每格10道的目标与缺口；不是模型性能热力图。':
      'Shows current complete candidates only, counting the target of 10 per cell and the gap by measured reasoning scale. It is not a heatmap of model performance.',
    '目录 v': 'Catalogue v',
  };
  const plural = (n, word) => `${n} ${word}${Number(n) === 1 ? '' : 's'}`;
  const RULES = [
    [/^显示 (\d+) \/ (\d+) 道完整候选 · 待独立审核$/, (m) => `Showing ${m[1]} / ${m[2]} complete candidates · awaiting review`],
    [/^(\d+) 道题 · 点击格子查看该格题目（细分到子领域的坐标系见下一张图）$/,
      (m) => `${m[1]} questions · click a cell to list them (the subdomain-level map is below)`],
    [/^原型目标 (\d+) · 每格按 10 道封顶的有效覆盖 ([\d ]+\/[\d ]+)(（\d+ 格空缺）)?。$/,
      (m) => `Prototype target ${m[1]} · coverage capped at 10 per cell ${m[2]}${m[3] ? ' (' + m[3].replace(/[（）]/g, '').replace(' 格空缺', ' cells empty') + ')' : ''}.`],
    [/^(\d+) \/ (\d+) 个有意义像素有题 · $/, (m) => `${m[1]} / ${m[2]} meaningful pixels have questions · `],
    [/^(\d+) 个空缺 · 二级子领域（叶子） (\d+) \/ (\d+) · 共 (\d+) 道。像素 = 一级子领域 × 解题推理尺度。$/,
      (m) => `${m[1]} empty · level-2 subdomains (leaves) ${m[2]} / ${m[3]} · ${m[4]} questions in all. A pixel is one level-1 subdomain at one reasoning scale.`],
    [/^查看 ([A-Z]{3}\d+) 详情$/, (m) => `Details of ${m[1]}`],
    [/^(\d+) 道（点题号看完整题目、附件与来源）$/,
      (m) => `${plural(m[1], 'question')} (click an id for the full question, its attachment and its source)`],
    [/^(.+) · (0\.1–1|1–10|10–100|100–1000) nm：(\d+) 道，点开看题号$/,
      (m) => `${m[1]} · ${m[2]} nm: ${plural(m[3], 'question')}, click to list their ids`],
    [/^(.+) · (0\.1–1|1–10|10–100|100–1000) nm：有意义但还没有题$/,
      (m) => `${m[1]} · ${m[2]} nm: meaningful, but no question yet`],
    [/^(.+) (0\.1–1|1–10|10–100|100–1000) nm：(\d+) 道，查看题目$/,
      (m) => `${m[1]} ${m[2]} nm: ${plural(m[3], 'question')}, see them`],
  ];

  const translate = (text) => {
    const key = text.trim();
    if (!key) return null;
    if (DICT[key] !== undefined) return text.replace(key, DICT[key]);
    for (const [pattern, build] of RULES) {
      const match = key.match(pattern);
      if (match) return text.replace(key, build(match));
    }
    return null;
  };

  let lang = 'en';
  try { lang = localStorage.getItem('geobench-lang') || 'en'; } catch (e) { /* private mode */ }
  window.geobenchLang = lang;
  const original = new WeakMap();

  const apply = (root) => {
    if (lang !== 'en') return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let node = walker.nextNode(); node; node = walker.nextNode()) nodes.push(node);
    for (const node of nodes) {
      if (original.has(node)) continue;
      const out = translate(node.textContent);
      if (out !== null) { original.set(node, node.textContent); node.textContent = out; }
    }
    const scope = root.querySelectorAll ? root : document;
    scope.querySelectorAll('[placeholder],[aria-label],[title]').forEach(el => {
      for (const attr of ['placeholder', 'aria-label', 'title']) {
        const value = el.getAttribute(attr);
        if (!value) continue;
        const out = translate(value);
        if (out !== null) el.setAttribute(attr, out);
      }
    });
  };

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'lang-switch';
  const paint = () => { button.textContent = lang === 'en' ? '中文' : 'EN'; };
  button.onclick = () => {
    lang = lang === 'en' ? 'zh' : 'en';
    try { localStorage.setItem('geobench-lang', lang); } catch (e) { /* private mode */ }
    location.reload();
  };

  const start = () => {
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
    paint();
    const nav = document.querySelector('header nav') || document.querySelector('header');
    if (nav) nav.after(button); else { button.classList.add('lang-float'); document.body.prepend(button); }
    const title = translate(document.title);
    if (title !== null) document.title = title;
    apply(document.body);
    let queued = false;
    new MutationObserver(() => {
      if (queued) return;
      queued = true;
      setTimeout(() => { queued = false; apply(document.body); }, 80);
    }).observe(document.body, {childList: true, subtree: true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
