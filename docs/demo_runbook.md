# Demo 运行与架构梳理

## 一键启动

```bash
# 首次运行前建议先填写密钥和数据库密码
cp .env.example .env
nano .env

# 启动后端 FastAPI + 前端 Streamlit
bash scripts/run_demo.sh
```

如果 8000 或 8501 端口被占用：

```bash
BACKEND_PORT=8010 FRONTEND_PORT=8510 bash scripts/run_demo.sh
```

如果 Neo4j 已启动且需要重新导入图谱数据：

```bash
RUN_IMPORT=1 bash scripts/run_demo.sh
```

检查 `.env`、Neo4j 连接和图谱数据量：

```bash
source .venv/bin/activate
python scripts/check_runtime.py
```

启动后访问：

- 后端接口文档：`http://127.0.0.1:8000/docs`
- 前端问答页面：`http://127.0.0.1:8501`

## 第一阶段增强功能

当前演示版已经从“普通聊天 Demo”升级为可展示 GraphRAG 技术链路的工作台：

- `智能问答`：回答下方会展示结构化推荐、知识图谱证据图、证据来源和 Agent 推理过程。
- `资料问答`：支持上传 PDF/txt 保险条款并围绕资料追问；图片入口保留，默认提示后续接入 OCR。
- `图谱探索`：输入实体或关键词后直接查看 Neo4j 子图，不需要另开 Neo4j Browser。

新增后端接口：

- `GET /graph/stats`：图谱节点与关系统计。
- `GET /graph/subgraph?query=高血压&depth=1`：返回可视化子图数据。
- `POST /documents/upload`：上传资料并抽取文本。
- `POST /documents/{document_id}/ask`：围绕上传资料进行临时 RAG 问答。
- `POST /admin/ingest-triples`：将审核后的三元组写入 Neo4j。

建议答辩演示问题：

```text
70岁老人有高血压，推荐什么保险？
北京5000元以下有哪些养老院？
上面第二个适合糖尿病老人吗？
```

## 性能优化说明

当前演示版针对 Streamlit 与本地 Neo4j 的常见卡顿点做了以下优化：

- 常见问题优先走规则意图解析，避免每轮都调用大模型做 JSON 解析。
- 只有检测到“上面、刚才、第二个、它”等指代追问时才调用问题重写 Agent。
- 单轮问答加入本地缓存，重复点击同一演示问题会直接命中缓存。
- 前端图谱统计缓存 30 秒，图谱探索缓存 120 秒，减少重复请求。
- 历史消息只轻量展示文本，只有最新回答渲染证据图和 Agent trace，避免 Streamlit 每次交互重复绘制大量 SVG。
- `/health` 改为轻量健康检查，不再每次阻塞式访问 Neo4j。
- Neo4j driver 设置连接超时与连接池上限，避免数据库异常时拖慢整个页面。

## 第二阶段增强功能

- 流式问答接口：`POST /chat/stream`，前端会优先使用 SSE 展示 Agent 执行轨迹和打字机式回答；失败时自动回退 `POST /chat`。
- 性能指标接口：`GET /metrics/demo`，展示平均延迟、缓存命中率、图谱命中率、规则过滤次数和图谱连接状态。
- 资料解析工作台：上传 PDF/txt 后可抽取三元组，先 `dry-run` 校验，再确认写入 Neo4j。
- StepChain 证据路径：每轮回答在图谱证据图下展示“用户条件 -> 规则过滤 -> 推荐实体”的可解释路径。
- 评测脚本：

```bash
source .venv/bin/activate
python scripts/eval_demo.py --api-root http://127.0.0.1:8000
```

评测报告会生成到 `reports/`，该目录是本地产物，已加入 `.gitignore`。

可选：启用真正的本地 embedding 模型，提升 HybridRAG 的语义召回质量。当前代码保留轻量字符向量兜底，如果模型下载或依赖安装失败，把 `KGQA_USE_EMBEDDINGS=0` 改回去即可，不会阻塞演示。

```bash
source .venv/bin/activate
python -m pip install -r requirements-embedding.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

然后在 `.env` 中增加或修改：

```env
KGQA_USE_EMBEDDINGS=1
KGQA_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
KGQA_EMBEDDING_DEVICE=cpu
KGQA_EMBEDDING_CACHE=.cache/kgqa_bge_small_zh_v15.pkl
```

首次运行前建议先预热并生成本地缓存：

```bash
python scripts/build_embedding_index.py
```

首次下载模型可能需要几分钟，并占用数百 MB 磁盘空间；建好缓存后，后续启动会直接读取 `.cache/kgqa_bge_small_zh_v15.pkl`。如果输出里 `use_bge : True`，说明已经启用 BGE 语义索引。之后重启 demo：

```bash
bash scripts/run_demo.sh
```

在问答结果的“证据来源”里，如果看到 `bge_embedding` 或更高的 `hybrid` 分数，就说明语义向量召回已经参与排序。

本地 Neo4j Desktop 推荐 `.env`：

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=kgqa

DEEPSEEK_API_KEY=sk-你的真实Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_REASONING_EFFORT=medium
DEEPSEEK_FALLBACK_MODEL=deepseek-v4-flash
DEEPSEEK_PRO_MIN_TOKENS=2048
DEEPSEEK_TIMEOUT=90

KGQA_USE_EMBEDDINGS=0
KGQA_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
KGQA_EMBEDDING_DEVICE=cpu
KGQA_EMBEDDING_CACHE=.cache/kgqa_bge_small_zh_v15.pkl
```

如果使用 `deepseek-v4-pro`，后端会自动按 DeepSeek 官方示例附加 `thinking: enabled` 与 `reasoning_effort` 参数；`deepseek-v4-flash` 则默认关闭 thinking 以保持低延迟。
如果主模型临时失败，系统会自动降级到 `DEEPSEEK_FALLBACK_MODEL`，避免演示现场直接中断。
`v4-pro` 的 thinking 会占用输出 token 且响应更慢；如果 `max_tokens` 太小，可能只返回 `reasoning_content` 而没有最终 `content`。系统已设置 `DEEPSEEK_PRO_MIN_TOKENS` 和 `DEEPSEEK_TIMEOUT`，并在最终内容为空时自动降级。

## 当前核心链路

1. 用户在 `frontend/streamlit_app.py` 输入问题。
2. 前端向 `POST /chat` 发送 `query` 和最近 6 条对话历史。
3. `src/api/main.py` 接收请求，调用全局 `RAGEngine`。
4. `RAGEngine` 先用 LLM 对多轮追问做问题重写。
5. `QueryParser` 再用 LLM 输出 JSON 意图，包括保险、疾病、养老院、年龄、城市、预算等字段。
6. `GraphRetriever` 根据意图拼 Cypher，从 Neo4j 检索疾病、药品、保险、养老院子图信息。
7. `RAGEngine` 把图谱检索结果、历史回答、当前问题拼进 Prompt。
8. `LLMIntegration` 调用 DeepSeek/OpenAI 兼容接口生成最终回答。
9. 前端展示回答，并在折叠区展示图谱上下文作为溯源。

## 文件结构

- `frontend/streamlit_app.py`：当前推荐使用的前端入口，包含页面样式、聊天历史、后端调用和溯源展示。
- `frontend/app.py`：较早版本的 Streamlit 前端，功能更朴素，可作为参考或废弃候选。
- `src/api/main.py`：FastAPI 服务入口，提供 `/chat` 和 `/health`。
- `src/graph_rag/rag_engine.py`：GraphRAG 总控，串联问题重写、意图解析、图谱检索和答案生成。
- `src/graph_rag/query_understanding.py`：LLM 意图识别，输出结构化 JSON。
- `src/graph_rag/graph_retriever.py`：当前实际使用的 Neo4j 检索器，按疾病、年龄、保险关键词、城市和预算检索。
- `src/graph_rag/graph_retrieval.py`：旧版通用子图检索器，目前没有接入主链路。
- `src/graph_rag/llm_integration.py`：OpenAI 兼容 LLM 客户端封装，支持从 `config.yaml` 和 `.env` 读取配置。
- `src/graph_rag/prompt_engineering.py`：较早的 Prompt 模板工具，目前主链路没有直接使用。
- `src/kg_construction/neo4j_loader.py`：结构化数据导入 Neo4j 的主脚本，会清空库并重建节点、关系和约束。
- `src/kg_construction/text_graph_builder.py`：保险条款文本到三元组的 LLM 抽取与入库流程。
- `src/kg_construction/ontology_design.py`：本体 schema 雏形，目前和导入脚本里的实际标签还没有完全统一。
- `src/kg_construction/entity_extraction.py`：NER/RE 抽象接口，当前仍是占位实现。
- `src/kg_construction/data_collection.py`：数据采集抽象接口，当前仍是占位实现。
- `src/utils/config_loader.py`：项目根目录、`.env`、`config.yaml` 的统一加载。
- `src/utils/logger.py`：全局日志配置。
- `config.yaml`：Neo4j、LLM、数据源的非敏感配置。
- `.env.example`：敏感配置模板。
- `DataCleaned/`：已清洗结构化数据，包括疾病、药品、保险、养老机构。
- `data/raw_text/sample_policy.txt`：文本条款抽取示例输入。

## 当前数据规模

- 疾病：403 条。
- 药品：3827 条。
- 保险产品：78 条。
- 养老机构：CSV 中 470 条。

## 当前短板

- 前端仍是 Streamlit demo，视觉和交互可以继续大幅升级。
- 意图识别完全依赖 LLM，缺少规则兜底和实体词典召回，未配置 Key 时问答链路会降级。
- Neo4j 检索是手写 Cypher 分支，缺少统一 schema、向量召回、排序评分和可解释证据链。
- 本体文件、导入脚本、检索脚本之间的标签命名还未完全统一。
- `entity_extraction.py` 和 `data_collection.py` 仍是接口占位，没有形成可展示的自动构图能力。
- 医养保险推荐的年龄合规性主要交给 Prompt，后端还没有确定性的年龄解析与过滤。
