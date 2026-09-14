# GeoBench Research Atlas

公开网站：https://k0ng1212.github.io/geometry-qa-builder/

网站与 QA 构建工具保存在同一仓库。GitHub Pages 使用 `main` 分支的 `/docs` 目录；提交网站变更后自动重新发布。无需安装依赖、支付托管费用或配置模型密钥。

## 日常迭代

- `data/catalog.json`：资源、候选条目、审核状态与公开示例。新增内容主要编辑这里。
- `index.html`：页面布局、研究框架说明。
- `styles.css`：颜色、字体、间距和手机适配。
- `app.js`：搜索、筛选、覆盖图、详情、CSV 导出。

新增论文：在 `resources` 中添加唯一 `id`，填写名称、原始链接、类型（research/database/benchmark）、摘要与整理状态。再在 `questions` 添加候选，`paper` 必须对应资源 ID。

候选能力取 perception / inference / design；领域暂取 quantum / chemistry / materials / biology。输入尺度与推理范围分开记录。新版地图展示 31 个任务规划方向，支持输入尺度/推理尺度切换和对数长度分箱。长度区间是规划参考，不是实例实测尺寸；任务方向与 26 条候选实例分开统计。尺寸测量协议仍待完善。

审核状态保留 needs_revision / pending_human_audit / numeric_checked_only。未完成实例的条目为草案。所有状态都不能自动视为正式可用题目。修改目录时同步 `counts`，首页与问题页中的统计说明也需要核对。

公开示例通过 `publicDemo: true` 标记，只有经过确认适合公开的 question、modelInput、answer 才能写入。其余候选仅提供目录元数据。GitHub 仓库及网站数据文件均公开，折叠答案不构成隐私保护。不要放入全文、密钥、内部证据、未授权附件或本地绝对路径。

## 本地预览与验收

在仓库目录运行 `python -m http.server 8765 --directory docs`，访问 http://localhost:8765/。直接双击 HTML 无法可靠加载 JSON。

发布前检查：统计与 JSON 一致；资源筛选、问题筛选、覆盖图跳转、详情展开、Esc 关闭、CSV 导出、空结果重置可用；390px 手机和桌面没有页面横向溢出；新增链接指向原始来源；公开数据不含内部材料。

第一版为研究目录，不是模型排名或已验证 benchmark。现有 26 条候选包含 8 条数值实例与 18 条待实例化草案，仅展示 2 道完整公开示例。

## Builder 模块工作台

builder.html 为独立页面，builder.css / builder.js 管理布局和交互。
每个模块的名称、边界和源码来自 builder_modules/mN_*/。
修改模块后运行 python tools/export_modules.py，更新 data/builder-modules.json。
只导出模块公开实现与说明，不读取 runs 或论文文件。页面不执行模型。

## 研究地图数据

- framework.js / framework.css：地图、任务卡片、尺度切换与筛选。
- data/task-framework.json：31 个任务方向与规划尺度。
- data/task-reviews.json / task-review.csv：首轮来源依据、可行性结论及导出表。

来源检查与优先级不代表专家认证，也不代表任务已具备可发布实例。
