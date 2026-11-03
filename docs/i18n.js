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
    '超导': 'Superconductivity', '磁性': 'Magnetism', '二维材料与莫尔物理': '2D materials & moire physics',
    '纳米与介观物理': 'Nano- & mesoscale physics', '原子与分子物理': 'Atomic & molecular physics',
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
    '这里只展示材料齐全、通过当前初筛的完整候选题；均待独立人工审核。 ·':
      'Only complete candidates that passed the current screening are shown; all still await independent human review. ·',
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
  };
  const plural = (n, word) => `${n} ${word}${Number(n) === 1 ? '' : 's'}`;
  const RULES = [
    [/^显示 (\d+) \/ (\d+) 道完整候选 · 待独立审核$/, (m) => `Showing ${m[1]} / ${m[2]} complete candidates · awaiting review`],
    [/^(\d+) 道题 · 点击格子查看该格题目（细分到子领域的坐标系见下一张图）$/,
      (m) => `${m[1]} questions · click a cell to list them (the subdomain-level map is below)`],
    [/^原型目标 (\d+) · 当前候选 (\d+) · 每格按 10 道封顶的有效覆盖 ([\d ]+\/[\d ]+) · 待独立人工审核 (\d+) · 正式通过 (\d+)。$/,
      (m) => `Prototype target ${m[1]} · candidates ${m[2]} · coverage capped at 10 per cell ${m[3]} · awaiting human review ${m[4]} · formally approved ${m[5]}.`],
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
