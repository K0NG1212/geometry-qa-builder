# Builder v0.3 · 七个可独立维护的模块

每个 m0_… 到 m6_… 目录包含 module.py（真实执行代码）、schema.json（契约）、
module.json（网站说明数据）、README.md（维护说明）。M2–M5 还有 prompt.md。
pipeline.py 只负责请求包、上下文、快照、接收、续跑和分支；旧 builder.py 保留共用基础能力及兼容检查。

修改对应模块，运行对应 test_mN_*.py；改字段契约时还需全流程测试。
更改代码/提示词后新建 run。旧 run 使用自身 pipeline_snapshot.py 和 builder_modules 快照。
modules/ 是 v0.2 的兼容存档，新版不从这里读取 AI 提示词。

网站内容通过 python tools/export_modules.py 从本目录生成。不要手改 docs/data/builder-modules.json。
