# 🧳 中国旅游攻略 Agent

> 输入"想去安阳玩3天"，输出完整旅游攻略——路线 + 景点 + 风土人情 + 拍照机位 + 预算，
> 景点/美食配**真实图片**，点击即可**跳转高德导航**。

## 快速开始

```bash
# 1. 配置 Key: 复制 .env.example 为 .env，填入 Dify / 高德的 API Key
cp .env.example .env

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 Web 界面 (推荐)
python app.py            # 打开 http://localhost:8000

# 或使用命令行
python main.py "想去安阳玩3天，喜欢人文历史"
```

## 三种运行方式

| 方式 | 命令 | 依赖 |
|------|------|------|
| Web 界面 | `python app.py` → http://localhost:8000 | Dify 工作流 |
| CLI (Dify 模式) | `python main.py "想去安阳玩3天"` + `--save` 存文件 | Dify 工作流 |
| CLI (直连 LLM) | `python main.py "云南7天" --direct` | DeepSeek/OpenAI 兼容 API |

Key 全部走 `.env` 或环境变量（见 `.env.example`），不再写死在代码里。

## 景点/美食的真实图片与一键导航

生成攻略时，富化层 (`tools/enrich.py`) 会为每个景点、每家美食店：

1. **高德 POI 搜索** → 拿到精确坐标（导航终点）和 POI 实拍图
2. **图片四层降级**：本地缓存 → 高德 POI 实拍图 → Wikimedia（可选）→ 高德静态地图
3. 图片落盘 `static/photos/{城市}/`，坐标/图片索引存 `_index.json`，重复生成直接命中缓存
4. 前端"🧭 一键导航"用高德 URI API（`uri.amap.com/navigation`），手机浏览器可直接唤起高德 App

## 项目结构

```
├── main.py                  # CLI 入口 (--direct 切换直连 LLM)
├── app.py                   # FastAPI Web 服务
├── config.py                # 配置 (读 .env)
├── orchestrator.py          # Dify 模式编排器
├── orchestrator_llm.py      # 直连 LLM 模式编排器
├── agents/                  # Agent 实现 (意图解析/路线规划/景点文化/攻略编译)
├── models/schemas.py        # Pydantic 数据模型
├── tools/
│   ├── dify_client.py       # Dify API 封装
│   ├── llm_client.py        # LLM 直连封装
│   ├── enrich.py            # 富化层: POI 坐标 + 真实图片 (核心新增)
│   ├── amap_utils.py        # 高德数字签名
│   ├── weather.py           # 高德天气
│   ├── json_utils.py        # 容错 JSON 解析 (共享)
│   └── image_scraper.py     # 可选: 离线抓图入库工具
├── frontend/                # Web 前端 (原生 JS)
└── static/photos/           # 图片本地缓存 (富化层写入)
```

## 架构

```
用户输入 → Dify意图解析 → Python补默认值
       → Dify路线规划 → Dify内容生成(按城市并行)
       → 富化: POI坐标 + 实景图片 (本地缓存优先)
       → Python编译 → 攻略输出 (Web / CLI / Obsidian)
```

## 依赖

- Python ≥ 3.10，依赖见 `requirements.txt`
- Dify 0.15+ (虚拟机部署) 或 DeepSeek API
- 高德开放平台 Key（天气/POI/静态地图/JS 地图）

## 📚 设计文档

- [项目知识库总览](docs/_index.md) — 架构、模块、流程、提示词导航
- [架构总览](docs/01-架构总览.md) — 六 Agent 协作拓扑 · 双模输出架构
- [项目全记录](docs/项目全记录.md) — 从设计到落地的完整历程
- [源码索引](docs/源码索引.md) — 代码文件 ↔ 设计文档对照
