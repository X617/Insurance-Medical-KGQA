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

本地 Neo4j Desktop 推荐 `.env`：

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=kgqa

DEEPSEEK_API_KEY=sk-你的真实Key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

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
