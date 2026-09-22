# GeoBench v0.4 原型执行规则

目标来自第四次会议及用户确认：4 个领域 × 4 个推理尺度，每格 10 道，各能力尽量 3 道，余下一道灵活安排。单尺度优先，输入尺度仍保存；大输入里的局部题不自动等于跨尺度。数量是目标，不是通过标准。

## 模块改动

- M0: prototype-policy.json 冻结于运行副本并进入 AI 请求；coverage.py 根据实测推理尺度统计 16 格缺口。
- M1/M2: 区分原始数据、论文、已有 QA；保存本地材料，化学身份/连接关系必须有证据。
- M3: 必填 learning_objective 和 selection_rationale；原子编号不能替代学科考点。
- M4: 题干明确实体身份、关系、索引、条件、单位；程序算答案。
- M5: disciplinary_meaning、entity_identity_clear、attachments_complete、single_scale_focus 四项必填检查；失败或不确定需修订。所有通过项仍为待人工审核。
- M6: student-packets/ 含完整题干、说明、XYZ 附件与索引；与 private-answers 分离。

## 操作

新运行使用当前 pipeline.py 初始化，按 RUNBOOK 请求/导入四个 AI 阶段。旧运行继续用各自冻结的 pipeline_snapshot.py，不能用新版本无痕替换旧审查结果。新规则与旧字段契约不兼容，必须新建运行。

python tools/export_modules.py 更新模块工作台。
python tools/export_prototype.py 更新16格缺口；候选只有显式 prototypeScreeningPassed 且 pending_human_audit 并有实测推理尺度才计入初筛进度，绝不表示正式可用。

## 验证与后续

本轮重新评估旧六题，并在真实 BCD 材料上完成 CNP001 改写运行；仅一项正例，未验证广泛生成质量。科学意义筛查不是可由字段非空或布尔值证明的事实，仍需独立审查和模型难度验证。

后续按缺口分批获取材料、生成和复审。现有评分器仅距离/夹角，设计无评分器时不得冒充完成。不能以同一个计算模板重复实例代替能力覆盖。

## 题库处置与审核状态分离

目录的 lifecycle 表示 active（当前原型）、rework（待重构）、backlog（待材料草案）、archived（历史归档）。status 仍表示原审核结果，不因目录整理而覆盖历史运行。每条保存 lifecycleReason、restartFrom 和处置日期，有新版替代时使用 supersededBy。

默认仅展示 active；初筛配额同时要求 active、prototypeScreeningPassed=true、pending_human_audit。旧数据未标注 lifecycle 时沿用原统计兼容行为，新目录必须显式标注。M6 导出的新候选不会自动成为正式题或进入 active；需先核对当前规则、材料完整性及审核结论，再更新网站目录。所有处置记录见 docs/data/qa-disposition.md。

## 统一目录准入统计

更新目录后依次运行 tools/export_prototype.py、tools/export_admission_audit.py、tools/export_modules.py。audit.html 展示每格缺口、待人工审核清单和每条记录的同一检查标准。准入统计仅检查材料字段、附件存在性和保存的初筛状态，不代替 M2–M5 重跑或领域审核；Q02 本轮另有真实新运行 q02-force-v04-001。规划方向编号与实际 QA 编号分开，Q02 对应 QNP001。目标160：初筛缺口与正式审核缺口分别报告。

## 公开题库准入与历史隔离

主图和问题池只展示完整、初筛通过的当前候选，不提供切换草案/历史的主界面选项。31个旧规划方向退出主图；16格仅按实际QA统计进度、能力分布和缺口。所有题目使用统一详情模板。旧草案、待重构及软件测试记录在 docs/history.html 保留，旧链接转到历史入口，不删除原始运行。新题按M0–M6构建，材料齐全与初筛通过后再进入当前题库；禁止用规划方向或占位题填充完成数。


## 2026-09-22 专项筛查补丁（M3/M5 0.4.1）
真实新任务和审核必须提交 geometry_audit。几何包括坐标、图像、距离、角度、晶格参数及空间关系；不等于必须读取 XYZ。删除全部相关几何后仍能获得主要分数的题不得放行。记录哪些评分依赖几何、尺度采用哪些参与实体、结论是否唯一/受条件限制、所属模板家族。程序只检查完整性和判断矛盾，AI 理由与科学语义仍待人审。

80 道既有候选已做静态专项审读：42 保留待审、32 小修后复查、6 重构。后两类暂停 active 配额，保留原题及冻结运行、原审核状态和原初筛标志；新处置以 lifecycle 和 focusedScreening 为准。不是重新执行 M0–M6，也不是外部模型消融实验。明细见 docs/screening.html 与 docs/data/focused-screening.json。修订应新建运行使用新规则，不能直接改原答案或旧 run。


## 第五次会议更新
当前方法按 [METHODOLOGY.md](METHODOLOGY.md) 的定义、构造、验证三步组织。M0–M6 是实现细节；优先按题型复用计算与验证，模板集中审查，实例程序全量检查并分层抽查。数值/选项/结构是三种目标输出；当前新增批量试跑仅实现最大间距和等权回转半径数值题。解释和论文证据保留审核侧，不默认给被测模型。设计选择与开放生成分开规划，未实现能力不冒称已接通。
