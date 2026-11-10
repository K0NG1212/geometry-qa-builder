# 骨架设计（codebase / 工作目录）

> 回答导师 2026-11-09 书面第 4 条：*You need to first design the scaffold of codebase/working directory, then you need to optimize your scaffold design, when it gets ready, ask LLM to implement → delete those you think not important*
>
> **他规定的顺序是三步，这份文件只走到第二步：**
>
> | 步 | 做什么 | 状态 |
> |---|---|---|
> | ① **设计** | 人（我们）定目录、职责、数据流、函数契约 | 本文件第 1–5 节 |
> | ② **优化** | 人自己先挑这版设计的毛病 | 本文件第 7 节 |
> | ③ **让 LLM 实现** | 定稿后才动代码 | 本文件第 8 节是待实现清单，**现在一行代码都没写** |
>
> 所以读这份文件的正确方式是：**先质疑第 2 节的目录划分和第 5 节的函数契约**。这两处定错了，后面实现得再漂亮也是错的。
> 状态：**draft，未经导师确认。** 日期 2026-11-10。

---

## 1. 六条设计原则

每条都写了「为什么」和「本项目踩过的坑」—— 原则不是凭空来的，是被坑出来的。

### 原则 1：按「谁写谁读」分目录，不按「文件类型」分

**为什么**：目录的意义是回答「我要改这件事该动哪里」。按类型分（all_scripts/、all_json/）就回答不了。

**坑**：`tools/` 现在有 60 个脚本，出题的、导出的、一次性调试的混在一起。想知道「改出题规则动哪个」只能靠文件名猜。

### 原则 2：生成物和手写物严格分开，而且目录名就要说清楚

**为什么**：手写的能改，生成的不能手改——手改了下次重跑就丢。两者混在一个目录里，没人分得清哪个能动。

**坑**：`docs/data/*.json` 全是生成物（规则已经写死：网站只读不改）。但做 B2、C1 时发现**手写内容无处可放**，只好新开了 `docs/content/`。这个区分应该从一开始就在目录结构里。

### 原则 3：教师侧和被测侧物理隔开，不靠纪律

**为什么**：答案泄漏是这类项目的头号事故。靠"记得别把答案放进去"一定会出事；靠目录隔离不会。

**坑**：第 5 次组会定的做法是"参考答案留审核侧、被测模型只看 `student/`"，于是每道题的文件夹里**同时**放了两份。第 10 次组会导师直接说去掉 `student/`——因为真正的隔离不是"同一个文件夹里分两个子目录"，而是**被测输入根本不从这个文件夹来**（现在由评测侧从 `docs/data/family-workbench.json` 生成）。

### 原则 4：每个产物都要能被一条命令重做，而且重做两次结果一样

**为什么**：这是导师的验收标准——"任何一个人、任何机器，看到这个文档下的所有信息，都可以创造出一个一模一样的 QA 题目出来"。

**已经做到的**：988 道题每道都有 `source/recompute.py`，导出时逐条执行，988/988 重算一致。`tools/export_qa_folders.py` 第二次跑写 0 个文件。

### 原则 5：外部数据要留出处，而且要能不联网重跑

**为什么**：论文里的每个数字都要说得出从哪来。同时，测试不能依赖网络。

**已经做到的**：`docs/content/external-counts.json` 每个数字标 `api`（附查询语句）或 `cited`（附出处与读取日期）；RCSB 的逐条目事实缓存在 `docs/content/pdb-entry-facts.json`，所以平时运行和测试都不联网。

### 原则 6：会腐烂的东西写成测试，不写成文档

**为什么**：文档不会报错。两份数据之间的一致性，只有测试守得住。

**坑**：空白格理由（69 条）和坐标图是两份数据，某个子领域一多个尺度，表就和图脱节，而**页面不会报错，只会静悄悄少一格理由**。所以 `tests/test_legend.py` 逐格对齐。同理 `tests/test_datasources.py` 盯"文档引的数字和生成文件对不对得上"。

---

## 2. 目标骨架

```
geometry-qa/
├── README.md              入口：这是什么、怎么跑起来
├── RUNBOOK.md             执行规程：出一批新题的 12 步
├── METHODOLOGY.md         方法学：定义 → 构造 → 验证
├── DATA_SOURCES.md        数据源：为什么是它、覆盖到什么程度
├── RELATED_WORK.md        相关工作与 baseline
├── SCAFFOLD.md            本文件
├── LICENSING.md           逐来源许可审计
├── PROJECT_STATUS.md      交接状态（只在顶部追加）
├── AGENTS.md / CLAUDE.md  两个助手共用的规则
│
├── generate/              ← 【出题】手写规则，人改
│   ├── families/              题型族：一个族 = 一个可参数化模板
│   ├── enumerators/           枚举器：把族 × 结构展开成实例
│   └── manifest.json          实例清单
│
├── verify/                ← 【核验】手写，人改。与 generate/ 不共享代码
│   ├── checkers/              独立检查器：换公式重算，判定正确选项
│   └── common.py              哈希、容差、报告格式
│
├── review/                ← 【审核】L0–L4 的工具
│   ├── sources.py             论文切片与证据定位
│   ├── stock.py               论文进题目文件夹 + 可点击核对页
│   ├── datasources.py         覆盖率统计
│   └── audit.py               准入检查
│
├── evaluate/              ← 【评测】被测模型在这里答题
│   ├── main.py                唯一入口（见第 5 节）
│   ├── exam.py                题 → prompt
│   ├── providers.py           模型接口（含 baseline 实现）
│   ├── scoring.py             判分
│   ├── report.py              分层汇总 + 置信区间
│   └── models.json            模型清单与单价
│
├── export/                ← 【导出】生成物的生产者，人改代码不改输出
│   └── *.py                   每个脚本一个产物，名字对得上
│
├── site/                  ← 【网站】
│   ├── *.html / *.js / *.css
│   ├── content/               手写文案（双语）—— 人改
│   └── data/                  生成物 —— 只读，不许手改
│
├── tests/                 谁都能改，但改测试要在 commit 里说清为什么
│
├── oneoff/                ← 【一次性】跑过就留着追溯，不进对外文档
│
└── archive/               ← 【归档】退役但还被引用的东西
    ├── builder-v03/           旧的逐题 AI 流程
    └── handoffs/              历次交接文件
```

**关键是四个边界，不是目录名好不好听：**

| 边界 | 两侧 | 为什么必须隔开 |
|---|---|---|
| **出题 ↔ 核验** | `generate/` ↔ `verify/` | 核验必须用**另一条算路**。同一份代码既出题又核答案，等于自己判自己的卷 |
| **手写 ↔ 生成** | `site/content/` ↔ `site/data/` | 生成物手改了下次重跑就丢。目录名就得让人一眼知道哪个能动 |
| **教师侧 ↔ 被测侧** | 题目 folder ↔ `evaluate/` 生成的 prompt | 答案泄漏靠结构隔离，不靠纪律 |
| **在用 ↔ 退役** | 其余 ↔ `oneoff/`、`archive/` | 对外呈现的 codebase 要干净（导师第 4 条后半句） |

---

## 3. 现状 vs 目标：差在哪

| 现状 | 目标 | 差距 | 代价 |
|---|---|---|---|
| `task_families/` 27 个文件 | `generate/families/` | 改名 | 低 |
| `enumerators.py`（根目录单文件） | `generate/enumerators/` | 单文件拆目录 | 中 |
| `templates/` 27 个（清单 + 分类树 + 模板） | 拆进 `generate/` 与配置 | **职责混着**：又放实例清单又放子领域树 | 中 |
| `checkers/` 18 个 | `verify/checkers/` | 改名 | 低 |
| `review_system/` 5 个 | `review/` | 改名 | 低 |
| `evaluation/` 9 个 | `evaluate/` + 补 `report.py` | **缺分层报告与置信区间** | 见第 5 节 |
| `tools/` **60 个**（出题/导出/一次性混在一起） | 拆成 `export/` + `oneoff/` | **13 个是一次性的** | 中 |
| `docs/` 兼当网站与文档 | `site/` | 改名；`docs/content` 与 `docs/data` 的区分已经有了 | 低 |
| 根目录 **29 个 .md**（8 个 `HANDOFF_*`） | 9 个 + `archive/handoffs/` | 归档 | 低 |
| `modules/`、`builder_modules/` | `archive/builder-v03/` | **各被引用 19 处**，动之前要改引用 | 中 |

**一句实话**：这些改动**没有一个会让题库变好**。它们只改变"别人打开仓库第一眼看到什么"。所以优先级低于补题和评测，但导师点名要，而且越晚改越贵。

---

## 4. 一条主数据流

从来源到报告只有一条主线。每一段标了落在哪个目录、产物是什么：

```
① 来源
   PDB / COD / QM7-X / SAMPL9 / 论文
   ↓  review/sources.py（论文切片）、review/datasources.py（覆盖率）
   产物：docs/content/external-counts.json、docs/data/source-coverage.json

② 实例
   题型族 × 结构 → 族实例
   ↓  generate/
   产物：generate/manifest.json（989 个实例）

③ 核验
   独立检查器重算，判定正确选项
   ↓  verify/
   产物：答案键 + 输入哈希

④ 教师侧 folder（质量核查用，不发给模型）
   source/{论文, data/, instruction.md, recompute.py} + QA.json + info.json
   ↓  export/export_qa_folders.py
   产物：D:\GeoBench-data\qa\<题号>\   （988 道，不进 Git）

⑤ 被测输入（独立于 ④ 生成，这是隔离的关键）
   ↓  evaluate/exam.py 从 docs/data/family-workbench.json 生成 prompt
   产物：prompt + 指纹

⑥ 跑分
   ↓  evaluate/main.py
   产物：runs/<run-id>/record.json（不进 Git）

⑦ 报告
   ↓  evaluate/report.py
   产物：分层表 + 置信区间 → 网站与论文
```

**④ 和 ⑤ 并列、不串联**，这是原则 3 的体现：教师侧文件夹里答案是摊开的（它本来就只给人看），被测输入另起一条路生成，两条路不交叉。

---

## 5. 评测侧的 main 与函数契约

导师第 4 条和组会 D2 点名要的就是这个：**先把 main 的几个函数定下来，让它 propose、你逐条读，再让它实现。** 下面只定签名和契约，**不写实现**。

现状：`evaluation/run.py` 已经是 main 的雏形，但**跑一遍就完**——没有重复、没有置信区间、没有捷径对照。而 `RELATED_WORK.md` 第 8 节已经证明这三样不是可选项。

```python
# evaluate/main.py —— 唯一入口

def main(argv=None) -> int:
    """命令行入口。子命令：run / report / baseline / budget。"""


def run(models:     list[str],          # 模型名，来自 models.json
        form:       str  = 'choice',    # 题型：四选一 / 开放
        setting:    str  = 'coords',    # 给模型看什么：坐标 / 图 / 坐标+图
        repeats:    int  = 5,           # ★ 每题重复几次
        ids:        list[str] | None = None,
        control:    str | None = None,  # ★ 捷径对照：None / 'no-name' / 'shuffled-structure'
        budget_usd: float | None = None,# 超预算就停，不是跑完才发现
        ) -> dict:
    """跑一次评测，返回可存盘的记录。

    契约：
      - 幂等：同样参数 + 同样题库 run → prompt 指纹相同；已答过的题读缓存，不重复花钱。
      - 可中断：任何时候杀掉，已答的部分不丢。
      - 记录里必须有：题库 run id、prompt 指纹、模型版本、repeats、control、实际花费。
      - repeats > 1 时每次调用都要留痕，不能只存聚合值。
    """


def report(record: dict,
           by:     tuple[str, ...] = ('ability', 'domain', 'scale'),  # ★ 分层维度
           ci:     float = 0.95,                                      # ★ 置信水平
           ) -> dict:
    """把一次（或多次）运行聚合成报告。

    契约：
      - 每个格子出的是区间，不是单点数。区间由 repeats 的 bootstrap 得到。
      - 几何题必须能单独看，不许被容易的题稀释（RELATED_WORK §8 第 2 条）。
      - 样本量不足的格子标 'n too small'，不出数字。
    """


def baseline(kind: str) -> 'Answerer':
    """不调用模型的参照线。kind ∈ {'random', 'majority', 'longest-option', 'human'}。

    契约：
      - random / majority / longest-option 必须在同一套 prompt 上跑，否则不可比。
      - 'human' 是人工作答的记录导入，不是模拟；没有记录就报错，不许拿模型冒充。
    """


def budget(models: list[str], repeats: int) -> dict:
    """跑之前先算钱：token 数 × 单价 × repeats。契约：只读，不发任何请求。"""
```

**四个 ★ 是现在没有、必须补的**：

| ★ | 为什么必须有 | 依据 |
|---|---|---|
| `repeats` | 单次跑分的排名不可信 | ProteinGeoBench：以每题跑一次计，**23.9% 的 bootstrap 重采样会把另一个模型排在第一** |
| `control` | 要能证明模型用了结构，不是读到了答案 | CARAT：19.3 分的提升里有 46.7 分来自"表示里根本没印出所需字段" |
| `by` 分层 | 几何题不能被查询题稀释 | ProteinGeoBench：数值题占 131 题中的 28 个，却占"四个模型全错的 12 题"的一半 |
| `ci` | 没有区间的单点数不能支撑结论 | 同上 |

**`human` baseline 的位置也先留好**：五篇同类工作里只有 MiSI-Bench 有人类线，但正因为有，它才说得出"SOTA 显著低于人类、微调 7B 在某类任务上反超"。先留接口，做不做再说。

---

## 6. 建议归档的（导师的 "delete those you think not important"）

**先说原则：不删，归档。** 理由——这些东西记录了"为什么当时那样做"，删掉就再也追不回来了；而导师要的是**对外呈现干净**，归档一样达到目的。

| 对象 | 现状 | 建议 | 风险 |
|---|---|---|---|
| `HANDOFF_2026-*.md` × 8 | 根目录 | → `archive/handoffs/` | 低。`CLAUDE.md`、`PROJECT_STATUS.md` 里的链接要同步改 |
| `LEGACY-v01.md`、`CLAUDE_HANDOFF.md`、`MEETING_2026-11-04.md`、`PROTOTYPE.md`、`DESIGN_CANDIDATES.md`、`EVIDENCE_CANDIDATES.md` | 根目录 | → `archive/` | 低，但 `EVIDENCE_CANDIDATES.md` 还在用（证据题的候选池），**要先确认** |
| `tools/` 里 13 个一次性脚本<br>（`fetch_a1`、`plan_a1`、`validate_a1`、`recompute_bio_batch`×2、`recompute_materials_batch`×2、`replay_demo`、`demo_independent_checker`、`inspect_run`、`triage_digest`、`prune_manifest`、`stabilize_manifest`） | 和在用脚本混在一起 | → `oneoff/` | 中。`RUNBOOK.md` 和测试里可能引用，要逐个 grep |
| `modules/`（7 个 md/schema）、`builder_modules/`（Builder v0.3） | 已归档的旧流程 | → `archive/builder-v03/` | **中高**：各被引用 **19 处**（测试、`docs/builder.html`）。动之前要改引用，不然网站和测试会断 |
| `examples/` | 3 处引用 | 先查清谁在用 | 未定 |

**一条自我约束**：根目录现在 29 个 `.md`，按上面归档后剩 **9 个**。但要注意——**新加的 `DATA_SOURCES.md`、`RELATED_WORK.md`、`SCAFFOLD.md` 都是我这两天加的**，也就是说我一边说"根目录太挤"一边在往里加文件。所以这三份要么是长期文档（我认为是，它们都要进论文），要么也该进子目录。**这一条留给导师定。**

---

## 7. 这一版设计自己知道的毛病（导师要求的 optimize 这一步）

把自己的设计挑穿，比等别人挑穿好。

| # | 毛病 | 我的倾向 |
|---|---|---|
| 1 | **改名的收益存疑**。`task_families/`→`generate/families/` 这类纯改名，收益只有"看起来整齐"，代价是所有 import、`RUNBOOK` 路径、网站链接、测试全要跟着动。**可能不值。** | 建议**只做低风险的两件**：`tools/` 拆出 `oneoff/`、根目录 `.md` 归档。改名那批**先不动** |
| 2 | **`templates/` 职责确实混**（实例清单 + 子领域分类树 + 模板），但它同时是 Codex 负责的目录。两个助手同时改一个目录的结构，很容易撞 | 要动先和 Codex 那边的分工对齐，**不能我这边单方面改** |
| 3 | **`oneoff/` 可能变成垃圾堆**。"一次性"目录往往有进无出 | 加一条规则：进 `oneoff/` 的脚本必须在文件头写**哪一次运行用的、产物在哪** |
| 4 | **第 5 节的 `repeats=5` 是拍的**。5 次够不够，取决于模型本身的方差，要先用免费额度实测再定 | 这正好接上组会 D3（用 Gemini Flash / OpenRouter 的免费额度先 debug 跑通） |
| 5 | **`control` 怎么实现没定**。"去掉名称"、"换结构但保持标签"都要动 prompt 生成，可能和现有的指纹机制冲突 | 这是定稿前必须想清楚的一处，否则 LLM 实现时会自己瞎定 |
| 6 | **整份设计没考虑 VLM 的图输入**。`setting='coords'` 之外的 `image` 路径现在只是个占位 | 看导师对 VLM 的优先级 |

---

## 8. 定稿后交给 LLM 实现的清单

**顺序有讲究：先补能立刻验证的，再动改名这种大范围的。** 每批都有验收标准，验收不过不进下一批。

| 批次 | 做什么 | 验收标准 | 风险 |
|---|---|---|---|
| **1** | `evaluate/report.py`：分层聚合 + bootstrap 置信区间 | 用已有的 `seeded` baseline 跑一遍，每格出区间；样本不足的格子标出来而不是出数字 | 低（纯新增） |
| **2** | `run()` 加 `repeats` 与缓存按 (题, 第几次) 分键 | 同样参数跑两次，第二次零模型调用；`repeats=3` 时记录里有 3 条痕迹 | 低 |
| **3** | `baseline()`：random / majority / longest-option | 三条线都在同一套 prompt 上跑出数字；`human` 无记录时报错而不是返回假数据 | 低 |
| **4** | `budget()`：跑前估价 | 只读、不发请求；估出的 token 数与实际跑完的差距报出来 | 低 |
| **5** | `control`：捷径对照两种 | 同一批题三种条件（正常 / 去名称 / 换结构）各跑一遍，差值能报出来 | **中**，要先定第 7 节第 5 条 |
| **6** | `tools/` 拆 `oneoff/`、根目录 `.md` 归档 | 全量测试仍然全绿；`check_links` 不报断链 | 中 |
| **7** | 改名那批（`generate/`、`verify/`、`evaluate/`、`site/`） | 同上 | **高**，且要先和 Codex 对齐分工 |

**批 1–4 现在就可以让 LLM 写**，它们只在 `evaluate/` 里新增东西，不碰题库、不碰网站、不碰 Codex 的目录。**批 5 要先补设计，批 6–7 要导师点头。**

---

## 9. 一句总结

这份设计真正要定的只有**第 2 节的四条边界**和**第 5 节的四个 ★**。目录改名是次要的，甚至可能不该做（第 7 节第 1 条）。

**四个 ★ 不是我的偏好，是别人用几千次试验证出来的**（见 `RELATED_WORK.md` 第 8 节）：没有重复和置信区间，我们报出来的任何排名都站不住；没有捷径对照，我们说不清模型是在读结构还是在读答案。
