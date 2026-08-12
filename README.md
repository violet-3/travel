# 🧳 中国旅游攻略 Agent

> 输入"想去安阳玩3天"，输出完整旅游攻略——路线 + 景点 + 风土人情 + 拍照机位 + 预算

## 两种运行方式

### 方式一：Dify 工作流（推荐）

```bash
# 1. 填 API Key
#    编辑 src/config.py，把 DIFY_API_KEY 填上

# 2. 安装依赖
pip install httpx pydantic

# 3. 运行
python src/main.py "想去安阳玩3天，喜欢人文历史"
```

### 方式二：直连 LLM（不依赖 Dify）

```bash
python src/main.py "云南7天" --direct
```

## 项目结构

```
src/
├── main.py                  # CLI 入口
├── config.py                # 配置文件（填 API Key）
├── orchestrator.py          # Dify 模式编排器
├── orchestrator_llm.py      # 直连 LLM 模式编排器
├── agents/                  # Agent 实现
│   ├── intent_parser.py     #   意图解析器
│   ├── route_planner.py     #   路线规划器
│   ├── attraction_culture.py#   景点推荐 + 风土人情
│   ├── guide_generator.py   #   攻略编译引擎
│   └── base.py              #   Agent 基类
├── models/schemas.py        # Pydantic 数据模型
├── tools/
│   ├── dify_client.py       # Dify API 封装
│   └── llm_client.py        # LLM 直连封装
└── knowledge/
    ├── route_templates.py           # 路线模板库
    └── route_templates_for_dify.md  # Dify 知识库源文件
```

## 架构

```
用户输入 → Dify意图解析 → Python补默认值
       → Dify路线规划 → Dify内容生成
       → Python编译Markdown → 攻略输出
```

## 依赖

- Python ≥ 3.10
- httpx, pydantic
- Dify 0.15+ (虚拟机部署) 或 DeepSeek API

## 设计文档

完整架构设计见 Obsidian 知识库：`05_项目实战/中国旅游攻略Agent/`
