---
tags: [MOC, project, agent, travel]
updated: 2026-10-20
status: active
---

# 山河游记 · 项目知识库

> **文档状态：** 当前 `app.py` 和 `main.py` 使用 LangChain 主链。部分早期架构、模块与流程页面记录的是 Dify、WebSocket、RAG、Obsidian 或媒体搜索设计目标，属于历史设计稿，不代表这些能力当前已接入。当前事实以 [`README.md`](../README.md)、[`docs/05-研发协作/README.md`](05-研发协作/README.md) 和实际源码为准。

## 当前实现入口

- [当前架构与源码索引](源码索引.md) — 运行入口、LangChain 主链、API 和保留的 Dify 旧链。
- [端到端生成流程](03-关键流程/端到端生成流程.md) — 当前 Agent 顺序、阶段超时、NDJSON、取消与导出。
- [媒体匹配流程](03-关键流程/媒体匹配流程.md) — 当前高德 POI/图片、可选 Wikimedia、本地缓存和真实性边界。
- [研发协作与迁移差异](05-研发协作/README.md) — 当前代码事实、Dify/LangChain 对照和迭代验证记录。
- [已批准的十轮迭代方案](05-研发协作/十轮迭代方案.md) — 固定验收场景与交付边界。
- [十一至十五轮迭代方案与实施记录](05-研发协作/十一至十五轮迭代方案.md) — 预算可信度、行程顺路、行前清单、攻略自检与生成缓存。

## 早期设计稿与历史记录

以下页面保留了项目早期构想或历史实现记录，不能单独用来判断当前功能是否上线：

- [早期架构总览](01-架构总览.md) — 原 Dify、双模输出与 WebSocket 设计。
- [项目全记录](项目全记录.md) — 早期 Dify 版本的实现过程与计划。
- [核心模块设计稿](02-核心模块/) — 包含 RAG、知识图谱、视频媒体、Obsidian 等未必在当前主链实现的目标。
- [提示词工程](04-提示词工程/) — 业务 Agent 的提示词素材，不等于运行时部署能力。

## 当前技术栈

| 层 | 当前实现 |
|---|---|
| Web API 与本机应用 | FastAPI，绑定 `127.0.0.1` |
| Agent 编排 | `orchestrator_llm.py`：LangChain 意图解析、路线规划、景点与文化 Agent |
| 模型调用 | `tools/llm_client.py`：OpenAI 兼容、Anthropic、Google GenAI LangChain adapter |
| 旅游数据校验 | Pydantic schema 与 Python 路线、约束、预算、行程可执行性与质量规则 |
| 外部补全 | 可选高德 POI、天气与地图图片；失败时保留文本攻略 |
| 行前与自检 | 天气驱动的备选方案与打包清单；六维度确定性质量评分 |
| 输出 | 原生 HTML/CSS/JS Web、CLI、Markdown、JSON、打印 |
| 历史数据 | 用户数据目录内的原子 JSON 文件与系统凭据库；无数据库 |
