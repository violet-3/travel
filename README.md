# 山河游记 · LangChain 旅游攻略 Agent

山河游记把旅行需求编排为路线、每日行程、景点、文化、美食、天气和预算攻略。当前 Web 与 CLI 主入口使用 LangChain；Dify 实现和部分设计文档作为历史资料保留，见[迁移说明](docs/05-研发协作/README.md#dify-历史链路与-langchain-主链)。

## 版本与运行环境

- Python 3.10 或更高版本；当前验证基线为 Python 3.10.6、Windows。
- 项目尚未定义独立的应用语义版本，也没有发布 tag；用 Git 工作区/commit 标识应用代码版本。
- 依赖范围见 [`requirements.txt`](requirements.txt)。Windows/Python 3.10 的可复现快照见 [`requirements-lock-py310-win.txt`](requirements-lock-py310-win.txt)；它是特定平台快照，不用于 macOS/Linux。
- 2026-10-20 干净 Windows 验证环境的主要依赖版本：FastAPI 0.150.0、Uvicorn 0.54.0、HTTPX 0.28.1、Pydantic 2.12.3、keyring 25.7.0、LangChain 1.4.6、langchain-openai 1.7.2、langchain-anthropic 1.7.6、langchain-google-genai 4.2.7、google-genai 1.75.0、Pillow 12.3.0、tzdata 2026.5。完整依赖快照在上面的 lock 文件中。

## 安装

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env } else { Write-Host ".env 已存在，跳过复制以保留现有配置。" }
```

要重现复核时的 Windows Python 3.10 环境，可以把安装命令改为：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements-lock-py310-win.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; else printf '%s\n' '.env 已存在，跳过复制以保留现有配置。'; fi
```

## 配置与启动

启动 Web：

```powershell
.\.venv\Scripts\python.exe -X utf8 app.py
```

macOS / Linux 在激活 `.venv` 后运行：

```bash
python -X utf8 app.py
```

打开 <http://127.0.0.1:8000>。服务默认只监听本机回环地址。

若 PowerShell 执行策略阻止 `start.ps1`，可直接使用下面的 Python 启动命令，无需更改系统执行策略。

Windows 也可以在 PowerShell 中运行 `.\start.ps1` 启动：脚本优先使用 `.venv`，也兼容 `venv`，不会自动安装依赖或改写 `.env`。首次启动前可运行 `.\.venv\Scripts\python.exe -X utf8 main.py --check` 做离线检查；它只检查依赖导入、数据目录写入能力和本地配置是否存在，不会连接模型或地图服务。缺少模型配置不会阻止网页启动，可打开“模型设置”补充。

模型可以在页面的“模型设置”里配置，也可以在 `.env` 中设置 `TRAVEL_LLM_URL`、`TRAVEL_LLM_KEY`、`TRAVEL_LLM_MODEL` 和超时、重试、Token 等可选参数。连接/结构化能力测试在点击相应测试按钮时就会发送短请求，可能产生少量费用；保存和读取配置不调用模型。API Key 优先存入操作系统凭据库；若凭据库不可用，只有明确选择“仅本次运行使用”才会把 Key 保留在当前进程内存。

攻略仍由现有 LangChain 主链调用 DeepSeek（或用户选择的其他模型）生成。可在“模型设置 → 景点网页资料与图片线索”主动开启 DeepSeek Search/Fetch；默认关闭。每次最多检索 3 个景点，每个景点最多 1 次 Search 和 1 次 Fetch，并行上限为 2。[DeepSeek 官方文档](https://api-docs.deepseek.com/zh-cn/guides/search/)列出的单次价格为 ¥5 / 1000 次成功且非空的 Search/Fetch 请求；单次攻略最多 6 次请求，最多约 ¥0.03。检索结果会显示为网页线索，票价不覆盖原预算。

联网凭据与攻略生成凭据相互独立：可以明确选择一个主机为 `api.deepseek.com` 的 DeepSeek 模型档案，或填写独立 Search Key；不会把其他厂商或代理档案的 Key 自动发送到官方域名。独立 Key 保存在系统凭据库；凭据库不可用时，可明确选择“仅本次运行”。环境变量方式需要显式设置 `DEEPSEEK_SEARCH_ENABLED=true`、`DEEPSEEK_SEARCH_AUTH_MODE=dedicated` 和 `DEEPSEEK_SEARCH_API_KEY`，只设置 Key 不会开启联网。配置详见[第十九至二十一轮实施记录](docs/05-研发协作/第十九至二十一轮实施记录.md)。

地图和 POI 配置是可选的。浏览器地图使用 `AMAP_JS_API_KEY` 与 `AMAP_JS_SECURITY_CODE`；服务端 POI、天气和图片使用 `AMAP_WEB_SERVICE_KEY` 与 `AMAP_WEB_SERVICE_SECRET`。缺少地图配置时仍可生成文本攻略。旧变量 `AMAP_WEATHER_KEY` 可继续作为 Web 服务 Key，`AMAP_REST_SECRET` 可继续作为服务端签名密钥。当前代码不再读取旧变量 `AMAP_SECRET`：迁移时请根据原凭据用途分别填写 JS 安全码或 Web 服务签名密钥，不要把一个值自动复制到两种用途。

也可在命令行生成并保存 Markdown：

```powershell
.\.venv\Scripts\python.exe -X utf8 main.py "想去安阳玩3天，喜欢人文历史"
.\.venv\Scripts\python.exe -X utf8 main.py "成都重庆5天，吃火锅看熊猫" --save
.\.venv\Scripts\python.exe -X utf8 main.py "苏州周末两日" --profile "本机档案ID"
.\.venv\Scripts\python.exe -X utf8 main.py "想去安阳玩3天" --web-research
.\.venv\Scripts\python.exe -X utf8 main.py --check
```

macOS / Linux 在激活 `.venv` 后运行：

```bash
python -X utf8 main.py "想去安阳玩3天，喜欢人文历史"
python -X utf8 main.py "成都重庆5天，吃火锅看熊猫" --save
python -X utf8 main.py "苏州周末两日" --profile "本机档案ID"
python -X utf8 main.py "想去安阳玩3天" --web-research
python -X utf8 main.py --check
```

CLI 默认使用本机已保存的默认模型档案；`--profile` 可以指定已保存档案。网页端“仅本次运行”的档案只存在于 Web 进程内，不会传递到独立 CLI 进程。没有已保存默认档案时，CLI 读取 `TRAVEL_LLM_*` 环境配置。`--save` 输出到仓库的 `output/` 目录，文件名会清理 Windows 禁用字符并限制在该目录下。

CLI 默认沿用本机保存的联网资料设置；`--web-research` 只为本次运行打开，`--no-web-research` 只为本次运行关闭。缺少 Search 凭据不会阻断文本攻略生成。

## 当前主链路

```text
用户需求 → LangChain 意图解析 → LangChain 路线规划
         → 景点 Agent 与文化 Agent 并行
         → 高德 POI/图片富化与按行程日期查询天气
         → 可选 DeepSeek Search/Fetch（最多 3 个景点、来源与图片线索）
         → 行程可执行性判断（已核验坐标）
         → 确定性校验和 Python 攻略编译
         → 行前清单与天气备选 → 攻略自检评分
         → Web / CLI / Markdown
```

Web 进度通过 `POST /api/generate/stream` 的 NDJSON `progress`、`guide`、`error` 事件传递。浏览器取消会断开请求并取消后端任务。成功攻略会写入本地历史，支持重新打开、Markdown/JSON 下载和打印；历史最多保留 30 条。

相同请求（描述、表单条件、模型档案与模型生成参数、上海自然日、高德配置身份及联网检索配置身份都一致）在 30 分钟内会复用上一次的成功结果，页面会明确提示“复用”并提供“强制重新生成”。缓存只存在本机，不保存失败或取消的结果，可用 `DELETE /api/cache` 清空。联网开关、Search 配置和 Key 的单向摘要参与缓存身份，避免启用与关闭状态互相复用；身份摘要不保存或回显原始密钥。

## 数据目录、迁移与恢复

用户级配置和历史 JSON 的默认目录：

| 系统 | 目录 |
|---|---|
| Windows | `%LOCALAPPDATA%\ShanheTravel` |
| macOS | `~/Library/Application Support/ShanheTravel` |
| Linux | `${XDG_CONFIG_HOME:-~/.config}/shanhe-travel` |

目录内的 `model-profiles.json`、`amap-settings.json`、`deepseek-search-settings.json` 和 `guide-history.json` 保存非敏感配置元数据及攻略历史；API Key 和高德凭据放在操作系统凭据库，不写进这些 JSON。仅本次运行的凭据只在当前进程内存。`guide-cache/` 存放短时生成缓存，可直接删除，不影响历史与配置。`SHANHE_TRAVEL_DATA_DIR` 可以在启动服务前指定另一份用户数据目录。项目 `.env`、`output/` 与 `static/photos/` 分别留在仓库目录，不受该变量移动；联网图片缓存写入 `static/photos/web-research/`。

迁移或备份时先停止服务，再复制上述用户目录；如需保留缓存图片，另行复制仓库里的 `static/photos/`；如需保留 CLI 输出，再复制 `output/`。复制到另一台设备不会迁移系统凭据库中的密钥，需在新设备重新录入模型与高德密钥。切换回原设备时，恢复 JSON 和原系统用户凭据可继续解析已有 profile。不要把真实 `.env`、凭据库导出或 Key 上传到仓库。

恢复损坏的数据前先停服务并备份整个用户目录。若单个 JSON 无法读取，将它移到备份目录后再启动：配置文件移走后重建对应模型/高德设置；历史文件移走后历史从空列表开始。JSON 使用原子替换写入，但备份仍应定期进行。`static/photos/` 是可再生成缓存，移除缓存不会删除用户配置或攻略历史，但之后可能重新请求外部图片服务。

旧环境变量 `TRAVEL_LLM_*` 继续由当前 LangChain 主链读取。旧模型档案 version 1 缺少 provider/protocol 字段时按自定义 OpenAI 兼容方式读取。`DIFY_*` 变量只供保留的旧 `orchestrator.py` / `tools/dify_client.py` 使用，当前 Web/CLI 不会自动切回 Dify。

## 已知限制

- 模型生成依赖用户提供的服务地址、Key、模型 ID 和所选结构化输出方式；无效 Key、限流或上游错误不会暗中切换到其他服务商。结构化兼容性需要通过用户主动点击的诊断或真实配置确认。
- 单元和集成回归用 mock/fixture 隔离外部调用，不证明真实模型或高德账号当前可用。本轮没有调用真实付费模型或高德服务。
- 天气仅使用能与路线日期匹配且仍在供应商预报范围内的数据；范围外会显示缺失状态。预算、门票、住宿、餐费与交通仍需按文中口径视为估算或待报价。
- 高德 POI 只对城市、名称和坐标通过校验的条目提供精确导航。静态地图依赖有效坐标、Key、网络及供应商接口，不能保证可用，也不是实景照片。缓存过期、缺失或损坏时会重试；图片缓存的远端 TTL 为 30 天。
- DeepSeek 网页资料仅在用户开启后调用。搜索结果先匹配城市和景点名，抓取正文再次核对；票价、来源机构及图片授权不会被自动认定或核验，网页票价不改预算。页面文字不会传给另一个模型。图片候选最多下载一张，下载请求限制公网地址、重定向、大小、类型和超时，并由 Pillow 解码后写入本地；失败时保留来源页链接。正文没有可用图片时会明确显示未提取到图片。
- 本轮使用 mock 与隔离复核脚本覆盖了 Search/Fetch 协议、来源归属、票价摘录、限流/取消、图片下载和凭据保存；没有真实 DeepSeek Search/Fetch 凭据，因此付费 API 和实时网页数据尚未实测。
- 服务定位为本机个人使用，不包含账号、多用户权限、公网部署防护、交易或机票酒店预订。
- 旧 Dify、WebSocket、RAG、Obsidian 和媒体搜索设计稿不代表当前 LangChain 主链具备这些功能；详见[文档状态说明](docs/_index.md)。

## 离线验证

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -X utf8 -B tests\smoke.py
node --test tests\frontend_stream.test.js
node --test tests\frontend_render.test.js
node --check frontend\js\app.js
node --check frontend\js\generation_stream.js
```

macOS / Linux（先激活 `.venv`）：

```bash
python -X utf8 -B -m unittest discover -s tests -p "test_*.py" -v
python -X utf8 -B tests/smoke.py
node --test tests/frontend_stream.test.js
node --check frontend/js/app.js
node --check frontend/js/generation_stream.js
```

冒烟与集成用例使用临时目录、mock 和无 Key 配置，不需要调用真实模型/高德服务。

## 项目文档

- [项目知识库与历史文档状态](docs/_index.md)
- [当前架构与源码索引](docs/源码索引.md)
- [研发协作、迁移差异与迭代记录](docs/05-研发协作/README.md)
- [已批准的十轮迭代方案](docs/05-研发协作/十轮迭代方案.md)
- [十一至十五轮迭代方案与实施记录](docs/05-研发协作/十一至十五轮迭代方案.md)
- [本机落地复核与第十六至十八轮验收](docs/05-研发协作/落地复核与第十六至十八轮验收.md)
