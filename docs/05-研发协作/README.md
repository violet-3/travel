# 山河游记 · 双角色研发协作

本目录提供两个可直接复制到独立会话的角色提示词，服务于本仓库的开发与决策复核。它们属于研发协作角色，与 `agents/` 中面向游客的业务 Agent 分工不同。

- [项目实现工程师](项目实现工程师提示词.md)：理解需求、提出必要取舍、实现改动、验证并交付。
- [决策复核官](决策复核官提示词.md)：独立核对方案与代码证据，判断是否值得做、是否实现正确、验证是否足够。

## 当前项目事实（2026-10-20）

以下结论按第 9 轮后的工作区重新核对；继续开发前仍应检查实际源码与依赖，不作为长期不变的架构约束。

| 维度 | 当前代码事实与依据 |
| --- | --- |
| 产品 | 山河游记：中国目的地攻略生成，涵盖每日行程、景点、文化、美食、预算，支持地图展示与导航。 |
| 主入口 | `app.py` 和 `main.py` 均使用 `orchestrator_llm.TravelOrchestrator`。 |
| 主链路 | 意图解析 → 路线规划 → 景点与文化两路并行 → 确定性校验 → 高德 POI/图片与按日天气补全 → Python 编译。见 `orchestrator_llm.py`。 |
| 模型调用 | `tools/llm_client.py` 使用 LangChain OpenAI-compatible、Anthropic 和 Google GenAI adapter、LCEL 与 Pydantic 结构化输出。 |
| 历史链路 | `orchestrator.py` 和 `tools/dify_client.py` 保留 Dify 工作流；当前主入口没有选用它，配置中仍有历史字段。 |
| 数据契约 | `models/schemas.py` 定义 `TravelIntent`、`RoutePlan`、`Spot`、`CultureData`、`TravelGuide` 等；`CultureData` 的嵌套内容大量采用 dict。 |
| HTTP 与进度 | `/api/generate` 返回攻略 JSON；`/api/generate/stream` 返回 NDJSON 的 `progress`、`guide`、`error` 事件；`/api/config` 提供前端地图配置。当前不是 WebSocket。 |
| 前端 | 原生 HTML/CSS/JS，九个内容页面（含行前准备）；米白、深绿、陶土色的东方旅行风格；现有地图以城市标记与连线为主。 |
| 富化与缓存 | `tools/enrich.py` 按本地图片 → 高德 POI 图片 → 可选 Wikimedia → 静态地图 → 留空的顺序降级；图片和索引写入 `static/photos/`。 |
| 天气与归档 | 当前 LangChain 主链已按城市及行程日期查询可用天气；CLI `--save` 保存最终 Markdown，并与 Web 共用持久化默认模型档案；无当前 Obsidian 自动归档。 |
| 本地数据 | 档案、地图设置和最多 30 条攻略历史存于用户应用目录；凭据单独存系统凭据库；不依赖数据库。 |
| 文档状态 | `docs/_index.md` 与源码索引标明历史设计稿；旧 Dify、WebSocket、RAG 和媒体视频设计不代表当前能力。 |

### Dify 与 LangChain 主链路的实际差异

| 能力 | Dify (`orchestrator.py`) | LangChain (`orchestrator_llm.py`, 当前主入口) |
| --- | --- | --- |
| 模型编排 | 调用历史 Dify 服务端工作流，需要 `DIFY_*` 配置及对应部署。 | 本地组合四个 LangChain Agent；支持 OpenAI-compatible、Anthropic 和 Google GenAI 协议。 |
| 失败处理 | 按旧 Dify API 的请求与重试逻辑运行，不接当前浏览器 NDJSON 取消闭环。 | 阶段超时、有界 Provider 重试、并行兄弟取消、SDK 客户端关闭和 Web 断连取消。 |
| 天气与媒体 | 按旧 Dify 流程和历史资料运行。 | 可选高德 POI/图片与按行程日期天气；失败时文本攻略仍可用，图片来源和缺失状态显式呈现。 |
| 输出与归档 | 旧代码包含 Obsidian 与早期输出设计。 | `GuideGenerator` 编译 `TravelGuide`；CLI 保存 Markdown，Web 提供本机历史及 Markdown/JSON/打印。 |

LangChain 是 `app.py` 和 `main.py` 的默认实现；Dify 代码保留为旧链路。两条链路功能不等价，新增功能应明确接入哪条链路，避免只修改旧编排器却影响不到当前入口。

## 历史复核线索（状态以迭代记录和当前源码为准）

以下是早期静态检查记录。相关问题已在后续轮次按迭代方案逐项处理；不要将列表当作当前未解决问题清单。

1. **结构化输出边界**：第 1 轮已为 `SpotList` / `CultureList` 的 Pydantic 实例、`items` 包装对象、旧列表与合法 JSON 文本增加显式转换和回归用例。后续修改 schema 时应维持非空业务标识检查和严格拒绝截断 JSON 的契约。
2. **迁移功能差异**：对照两个编排器核实天气、穿衣建议、Obsidian 归档、进度阶段与异常行为，不能仅因旧链路有实现就认定主入口具备。
3. **前后端天气字段**：`tools/weather.py` 输出 `day_weather`、`day_temp` 等字段；前端天气渲染读取 `dayweather` 等字段。接入主链路前应明确映射。
4. **预算与日期可信度**：预算编译器含固定往返交通加项、日均门票与住宿下限，`total_budget_est` 并非最终预算直接来源；日期提示词含固定年份示例，文化生成使用当前月份。需要区分估算、用户出行日期与已核验信息。
5. **地图与图片真实性**：城市连线不等于道路规划；城市中心不等于景点精确坐标；静态地图与随机占位图不等于景点实拍。关注同名 POI、经纬度顺序、图片错误匹配与失败缓存。
6. **测试副作用**：`tests/smoke.py` 第 1 轮已固定空 AMap 配置、阻断 HTTP、把图片索引与 `fake` 图片放进临时目录。新增测试应沿用 mock 和临时目录，不运行真实模型/高德调用。

第 1 轮已运行离线结构化输出回归测试、隔离冒烟测试与 Web/CLI 启动兼容检查；没有调用真实模型或高德接口，因此完整攻略的外部链路仍未验证。

### 第 1 轮实施与验收记录（2026-10-20）

- `agents/attraction_culture.py` 统一接收 Pydantic 包装、`items` 对象、单条对象、dict/model 列表和合法 JSON 文本；景点必须有 `name`，文化记录必须有 `city`。空结果、非法类型、空业务记录和截断 JSON 明确抛 `AgentOutputError`，不再用容错截断修补后当作完整结果。
- `tests/test_agent_output.py` 覆盖景点/文化转换形态及失败契约；`tests/smoke.py` 在临时图片目录运行，清空 AMap 配置并替换 HTTP 客户端，确认没有 HTTP 请求。
- 实际命令：`venv\\Scripts\\python.exe -B -m unittest discover -s tests -p "test_agent_output.py"`（3 项通过）；`venv\\Scripts\\python.exe -B tests\\smoke.py`（全部通过）；离线环境下导入 `app` 和运行 `main.py` 无参数用法检查通过。
- 决策复核官独立确认上述两条测试通过，并报告 `static/photos` 下两份文件的 SHA256 与运行前一致。此项为独立复核报告，不是本会话自行计算。
- 未验证真实模型结构化调用、高德服务、完整 Web 生成请求和完整 CLI 生成；本轮没有触发这些外部链路。

### 第 2 轮实施与验收记录（2026-10-20）

- 新增不可变 `ModelConfig` 快照、按请求构造的 `LLMClient`，并将同一请求的客户端显式注入四个 LangChain Agent；Web 与 CLI 均在生成开始时解析配置。移除了进程级 LLM 单例。
- 保留 `TRAVEL_LLM_URL/KEY/MODEL`，新增温度、超时、重试、最大输出 token 与结构化输出方式环境项。API Key 使用 `SecretStr`，不进入配置的 `repr` 和常规 `model_dump`；没有命名配置仓库时，非空 `profile_id` 明确返回 422。
- 本会话实际运行：`venv\\Scripts\\python.exe -B -m unittest discover -s tests -p "test_model_config.py" -v`（10 项通过）；第 1 轮解析回归（3 项通过）；隔离 `tests/smoke.py` 全部通过。离线 Web 导入和 CLI 无参数用法也通过。
- 决策复核官独立运行 `python -B -X utf8 -m unittest discover -s tests -p test_*.py -v`，报告 13 项通过及 `git diff --check` 通过。本轮未访问模型服务。
- 留待第 3 轮：配置文件与系统凭据库、命名配置存取和浏览器设置页。留待第 4 轮：不同供应商对结构化输出策略的兼容诊断。

### 第 3 轮实施与验收记录（2026-10-20）

- 新增 Web 模型设置页和命名配置 API：支持创建、编辑、删除、设默认、生成时选择配置及单独清除密钥。编辑密钥留空会沿用已保存密钥；密钥输入框不回填，也没有写入 `localStorage` / `sessionStorage` 的逻辑。
- 模型档案的非敏感字段以原子替换 JSON 保存到用户应用数据目录；API Key 通过 `keyring` 写入操作系统凭据库。凭据库不可用时，只有显式勾选“仅本次运行”才会在内存中保留密钥，进程重启后档案和密钥一起失效。`SHANHE_TRAVEL_DATA_DIR` 可用于指定隔离的数据目录。
- Web 默认绑定 `127.0.0.1`。请求边界拒绝非本机 Host，并对 API 写请求校验 Origin 与页面来源一致。请求校验错误只返回字段位置和通用说明，不回显原始输入；生成失败也改为安全的通用消息。
- 默认档案在每次 Web 请求开始时解析为不可变 `ModelConfig` 快照；显式选择的档案覆盖默认档案。未设置档案时 Web 与 CLI 继续兼容 `TRAVEL_LLM_*` 环境配置。模型配置字段校验在请求边界返回 422。
- 第 3 轮回归用例覆盖：凭据重启恢复、密钥不进入 JSON/API 响应、临时配置编辑后仍可解析、默认档案选择与删除、显式清除密钥、凭据库不可用、写盘失败回滚、错误 Host/Origin、恶意校验输入不回显及生成异常不泄露密钥。
- 本会话实测：`venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -p "test_*.py" -v`（21 项通过）；`venv\Scripts\python.exe -B -X utf8 tests\smoke.py`（全部通过，HTTP 被隔离）；`node --check frontend/js/app.js`、Web 导入、CLI 无参数用法和 `git diff --check` 通过。没有调用模型 API 或写入真实凭据库。
- 浏览器实测设置弹窗在 390×844 视口内可滚动显示；修复后手机输入框宽 318 px、页面无横向溢出，头部操作改为两列，八页导航保留自身横向滚动且“主屏”按钮在可视区域。桌面端也能打开设置弹窗。复核官此前独立测过 UI 新建、设默认、编辑空密钥和保存流程。
- 当时的记录把 JS Key 与旧 `AMAP_SECRET` 视作 `/api/config` 的历史字段。第 7 轮已拆分浏览器 JS Key/安全码与服务端 Web Key/签名密钥；当前代码不读取 `AMAP_SECRET`，迁移说明见根目录 README。
- 决策复核官已独立确认第 3 轮通过：报告 21 项单元测试、隔离冒烟与 390×844 设置页复验通过；未调用模型 API，也未写入真实凭据库。第 4 轮已进入实施。

### 第 4 轮实施与验收记录（2026-10-20）

- 已开始适配多服务商模型：保留 OpenAI 兼容通用客户端，新增 Anthropic Claude 与 Gemini 的 LangChain 原生客户端；设置页提供 DeepSeek、Qwen、GLM、Moonshot/Kimi、豆包/火山方舟、Claude、Gemini 预设。预设仅填入可编辑建议值，不代表模型或 Key 已实测；模型 ID 允许手填，不请求 `/models`。
- `ModelConfig`、配置 payload 与档案记录增加 provider/protocol；旧 version 1 档案缺少新字段时按 `custom` / `openai_compatible` 读取。温度允许为空，客户端构造器省略空值；原生协议分别使用对应 LangChain 包及参数映射。
- 结构化输出策略可显式选 Function calling、JSON Schema、兼容协议 JSON mode 或严格 JSON 文本。Claude/Gemini 原生协议禁用 JSON mode；严格文本会把 Pydantic schema 写进提示，执行 `json.loads` 与 Pydantic 校验，解析失败直接失败，不做截断或修复。不会因鉴权、限流或未知错误自动更换协议或服务商。
- 每份配置提供独立的“测试连接”和“测试结构化”按钮；点击按钮即发送短请求，可能产生少量费用。配置读取、创建、编辑和保存不调用模型；诊断严格使用该档案，并在页面仅显示“未实测”或当前会话的诊断结果。保存、清密钥或删除配置会清除旧结果，版本令牌阻止过期的在途结果覆盖新状态。
- 诊断错误分类为鉴权、模型不存在、超时、限流、结构化输出不支持、未知；响应只使用固定安全文案，不回显上游异常或 Key。连接成功要求收到非空文本，结构化成功要求 Probe Pydantic schema 校验通过。
- Key 绑定检查：服务商、协议或 URL scheme/主机/端口改变时，已有凭据必须重新填写；也可先单独清除旧凭据。相同 origin 下仅修改路径允许留空沿用。
- Python 3.10.6 环境中按适配包约束安装 `langchain-anthropic>=1.7,<2`、`langchain-google-genai>=4.2.7,<4.3` 与 `google-genai>=1.65,<2`；为兼容该共享虚拟环境现有约束，Pydantic 使用 `>=2.7.4,<=2.12.3`。原生 schema 能力与可编辑接口建议值参考 [LangChain Anthropic](https://docs.langchain.com/oss/python/integrations/chat/anthropic)、[LangChain Google GenAI](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai)、[DeepSeek](https://api-docs.deepseek.com/quick_start/pricing-details-cny/)、[阿里云 Model Studio](https://help.aliyun.com/en/model-studio/base-url)、[智谱](https://open.bigmodel.cn/claw-plan-team)、[Kimi API](https://platform.kimi.com/docs/api/chat) 和[火山方舟](https://docs.volcengine.com/docs/ark/compatible-with-openai-sdk?lang=zh)官方文档；预设模型名不视为已验证。
- 所有提供商诊断和适配测试均使用 mock 或只构造 LangChain 客户端，不发送真实模型请求。第 4 轮独立复核已通过；之后各轮的验证记录按下方新增条目更新。

### 第 5–9 轮实施与验收摘要（2026-10-20）

- **第 5 轮：旅行需求规范化。** 自由文本、显式目的地/日期/天数/同行人/预算与硬约束合并到 `TravelIntent`；日期按 Asia/Shanghai 解析，明确表单值优先；Agent 上下文保留约束。
- **第 6 轮：路线与预算校验。** 检查天数、日序、城市覆盖和城际交通边；区分人均/团体、住宿晚数、估算小计与待核价交通；一日游住宿按 0 晚。
- **第 7 轮：地图、POI 与天气闭环。** 拆开高德浏览器 JS 凭据与服务端 Web 凭据；POI 核对城市/名称/坐标，路线天气按实际城市和日期查询；缺 Key 或服务不可读时降级为文本。
- **第 8 轮：图片来源与缓存安全。** 缓存路径哈希化、图片完整解码校验、图片/坐标独立 TTL、并发索引原子合并；页面显示来源和日期，位置核验不等于票价/营业信息核验。第 8 轮独立复核通过。
- **第 9 轮：生成可靠性与本机历史。** 增加阶段超时、并行兄弟取消、SDK 根资源关闭、provider usage/耗时、严格 NDJSON、浏览器停止到后端取消、本地原子 JSON 历史、Markdown/JSON/打印和复制失败提示。独立复核报告通过；实现环境全套 91 项 Python、隔离冒烟、3 项 Node 流用例通过。
- 验证均为离线/mock/临时数据，不调用真实模型或高德付费接口；真实服务兼容性仍由实际账号和所选 Provider 决定。

### 第 10 轮实施与验收记录（2026-10-20）

- 增加可复现的 Windows/Python 3.10 依赖锁定快照；主依赖声明包含 UTF-8 编码标记与 `tzdata`，为 Windows `ZoneInfo("Asia/Shanghai")` 提供时区数据。README 分开列出 Windows 虚拟环境解释器与 macOS/Linux 激活后的启动/CLI 命令；复制 `.env.example` 仅在 `.env` 不存在时进行，以免覆盖已有凭据配置。
- 固定离线编排场景覆盖单城 3 日、多城 7 日、一日游、亲子、老人少走路、低预算、跨年天气日期和无地图 Key 文本降级。另有专项测试覆盖错误模型 Key/429 分类、并发请求配置隔离、流式取消与后端任务取消。
- 多人表单覆盖模型默认“独自”时，归一为“同行（关系未注明）”；保留模型明确给出的亲子/朋友等关系，也不因人数为 1 擅自改写明确关系。
- 将旧架构总览与项目全记录标为 Dify 早期历史文档，并说明当前 LangChain 主入口。迁移说明同步明确当前代码不读取旧 `AMAP_SECRET`；用户需根据凭据用途分别配置 JS 安全码或服务端签名密钥。
- 本会话实测：增加 ASGI 断连异步清理回归后，95 项 unittest 通过；隔离 `tests/smoke.py` 通过且未发 HTTP；Node 流测试 3 项通过；JS 语法检查与 `git diff --check` 通过。
- 决策复核官在浏览器端复验：停止生成约 0.4 秒内取消 mock 工作且不写历史；同一临时数据目录重启后可恢复并打开攻略，不触发新模型调用；390px 手机主屏与设置窗无横向溢出；实际 Markdown/JSON 下载检查了内容与无密钥泄漏。打印样式已做静态调整，未实际保存系统 PDF。
- 决策复核官最终独立复核通过（离线验收范围）：全新 Windows/Python 3.10.6 环境的 95 项 unittest、3 项 Node 流测试、隔离 smoke、JS 语法、`git diff --check` 均通过，`pip check` 报告依赖无冲突。完整 ASGI 断连原始复现也由复核官确认异步关闭完成；第 10 轮复核记录见[十轮迭代复核记录](十轮迭代复核记录.md)。
- 当前项目虚拟环境的 `pip check` 仍报告 `hf-gradio` / `gradio-client` 版本冲突；它不属于本项目依赖链，且独立干净验证环境没有该冲突。本轮新增的 `anyio>=4,<5` 与 Windows 锁文件中 `anyio==4.15.1` 一致。
- 本轮所有服务侧验证使用 mock/fixture/临时目录；没有调用真实模型或高德付费服务。系统 PDF 未实际保存，非 Windows 实机未实测；真实外部服务能力不由离线复核结论保证。

### 第 11–15 轮实施与验收摘要（2026-10-20）

十轮之后按"攻略是否好用"继续迭代五轮，方案与逐轮细节见[十一至十五轮迭代方案](十一至十五轮迭代方案.md)，自查清单见[复核记录](十一至十五轮复核记录.md)。

第十六至十八轮继续修正预算边界、缓存隔离与本机 CLI 启动体验，实施及验证证据见[本机落地复核与第十六至十八轮验收](落地复核与第十六至十八轮验收.md)。

- **第 11 轮：预算可信度。** 门票由固定日均 `100 × 天数` 改为按行程实际地点累加（无标价按每处 ¥100 估算并列出待核实清单）；住宿按过夜城市等级系数折算；新增门票拆分、住宿口径与费用结构占比。同时修复 `guide_generator.py` 被污染模块 docstring。
- **第 12 轮：行程可执行性。** 新增 `tools/itinerary_feasibility.py`，只用已核验坐标计算同日通勤距离与单日里程，按节奏校验活动数与粗估耗时，输出 0–100 评分与逐日问题。无坐标时明确"无法判断"。
- **第 13 轮：行前准备。** 新增 `tools/prep_plan.py`，按天气给逐日室内备选、高温/低温/大风提示，并按温度、天数、同行关系与硬约束生成分组打包清单。前端新增第 9 个页面"行前"。
- **第 14 轮：攻略自检。** 新增 `tools/guide_quality.py`，六维度加权评分（结构、需求、内容、预算、位置、可执行）并输出可改进项。分数只衡量完整度与边界说明，不是事实核验。
- **第 15 轮：生成缓存。** 相同请求 30 分钟内复用成功结果，key 含表单条件、档案与模型身份但不含 API Key；命中显式标注并提供强制刷新，新增 `/api/cache` 查询与清空。

本会话实测：179 项 unittest、隔离 smoke、3 项流测试、9 项前端渲染测试与两份 JS 语法检查通过；服务端 `/` 与 `/js/app.js` 可正常访问；另用构造的"北京人文三日"样例跑通 预算 → 可执行性 → 行前 → 自检 全链路。新增测试 93 项，全部使用临时目录与桩对象。**本轮由同一会话实现并自查，没有另开独立复核会话**；前端只做了内容级渲染回归，未在真实浏览器做视觉检查或 390px 截图。外部服务与真实模型仍未调用。

## 使用方式

1. 将“项目实现工程师提示词”全文交给负责开发的会话，随后补充具体需求。
2. 需要决策复核时，将“决策复核官提示词”全文交给另一会话，并提供需求、实现方案、当前 diff 或分支及验证记录。两边都应能读取同一仓库。
3. 普通局部修复可以先实现后复核；涉及编排器迁移、数据结构、依赖或外部调用策略的变更，先复核方案再实施。
4. 实现角色提交证据，复核角色独立读取；发现阻断问题后由实现角色修复，再针对修改复核。复核通过表示在检查范围内满足约定，不代表自动发布或线上可用。

日常沟通可直接复制以下任务头：

```text
本次需求：
用户可见的预期行为：
范围与明确不做的内容：
验收场景：
实现方案 / 待复核决策：
相关文件、diff 或提交：
已运行检查及结果：
外部调用与验证限制：
```

信息不全时，两个角色应先检查可获得的代码与上下文，能合理判断的细节自行处理；只有影响目标、接口或不可逆操作的关键缺失才需要向用户澄清。
