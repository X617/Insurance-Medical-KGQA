# 各模块框架接口说明

本文档汇总各模块对外暴露的类、函数及主要方法签名，便于实现与联调。

---

## 1. 知识图谱构建 `src/kg_construction/`

### 1.1 `ontology_design.py` — OntologyDesign

| 成员 | 类型 | 说明 |
|------|------|------|
| `ENTITY_TYPES` | class attr | `Dict[str, List[str]]` 实体类型 → 属性列表 |
| `RELATIONSHIPS` | class attr | `List[Tuple[str,str,str]]` (头类型, 关系, 尾类型) |
| `get_entity_types()` | classmethod | 返回实体类型与属性 |
| `get_relationships()` | classmethod | 返回关系列表 |
| `get_entity_labels()` | classmethod | 返回所有实体标签 |
| `get_schema_for_entity(entity_type)` | classmethod | 返回指定类型的属性 schema |

### 1.2 `data_collection.py` — DataCollector

| 方法/属性 | 签名 | 说明 |
|----------|------|------|
| `__init__(config?)` | 构造函数 | config 含 medical/insurance 等数据源路径列表 |
| `set_base_path(base_path)` | 无返 | 设置项目根路径 |
| `get_medical_sources()` | → List[str] | 医疗数据源路径 |
| `get_insurance_sources()` | → List[str] | 保险数据源路径 |
| `load_medical()` | → Dict[str, Any] | 加载医疗数据 |
| `load_insurance()` | → Dict[str, Any] | 加载保险数据 |
| `load_all()` | → Dict[str, Dict] | 加载全部，返回 {"medical":..., "insurance":...} |

### 1.3 `entity_extraction.py` — EntityExtractor

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__(model_name?, **kwargs)` | 构造函数 | NER/RE 模型名或路径 |
| `extract_entities(text)` | → List[Dict] | 单文本实体抽取 |
| `extract_entities_batch(texts)` | → List[List[Dict]] | 批量实体抽取 |
| `extract_triples_from_text(text)` | → List[Triple] | 从文本抽三元组 |
| `extract_triples_from_records(records, schema)` | → List[Triple] | 从结构化记录按 schema 生成三元组 |

### 1.4 `neo4j_loader.py` — Neo4jLoader

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__(uri, username, password)` | 构造函数 | Neo4j 连接参数 |
| `connect()` / `close()` | 无返 | 连接管理，支持 with |
| `create_constraints_and_indexes(ontology)` | 无返 | 按本体建约束与索引 |
| `load_triples(triples, head_label?, tail_label?, merge?)` | → int | 批量写三元组 |
| `clear_graph()` | 无返 | 清空图（慎用） |
| `run_cypher(query, parameters?)` | → List[Dict] | 执行 Cypher |

---

## 2. GraphRAG 引擎 `src/graph_rag/`

### 2.1 `query_understanding.py` — QueryUnderstanding / QueryIntent

**QueryIntent**（dataclass）：`raw_question`, `intent`, `entities`, `keywords`

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__(ner_model?, intent_labels?)` | 构造函数 | 可选 NER 与意图标签 |
| `parse(question)` | → QueryIntent | 解析问句 |
| `get_entities(question)` | → List[str] | 仅返回实体列表 |
| `get_intent(question)` | → str | 仅返回意图 |

### 2.2 `graph_retrieval.py` — GraphRetriever / SubGraphResult

**SubGraphResult**：`nodes`, `relationships`, `triples`

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__(neo4j_loader, max_hops=2)` | 构造函数 | 图库客户端与默认跳数 |
| `retrieve_subgraph(entities, hops?, limit?)` | → SubGraphResult | 按实体检索子图 |
| `subgraph_to_text(result)` | → str | 子图转文本供 Prompt 使用 |

### 2.3 `prompt_engineering.py`

| 名称 | 类型 | 说明 |
|------|------|------|
| `PROMPT_TEMPLATE` | str | 含 `{graph_context}`、`{question}` 的模板 |
| `build_qa_prompt(graph_context, question, template?, **kwargs)` | → str | 组装问答 prompt |
| `get_system_prompt(role?)` | → str | 系统角色 prompt |

### 2.4 `llm_integration.py` — LLMIntegration

| 方法 | 签名 | 说明 |
|------|------|------|
| `__init__(model_type, model_path?, api_key?, api_base?, **kwargs)` | 构造函数 | local / api 模式 |
| `chat(messages, temperature?, max_tokens?, **kwargs)` | → str | 多轮对话 |
| `generate(prompt, system_prompt?, temperature?, max_tokens?, **kwargs)` | → str | 单轮生成（RAG 用） |
| `stream_generate(...)` | → Generator[str] | 流式生成（可选） |

---

## 3. API `src/api/main.py`

| 路由/依赖 | 说明 |
|-----------|------|
| `GET /` | 服务说明与链接 |
| `GET /health` | 健康检查，返回 HealthResponse(status, neo4j?, llm?) |
| `POST /qa` | 问答，请求体 QARequest(question, max_hops?, temperature?)，响应 QAResponse(answer, sources?, graph_context?) |
| `get_graph_retriever()` | 依赖注入，返回 GraphRetriever |
| `get_llm()` | 依赖注入，返回 LLMIntegration |

---

## 4. 工具 `src/utils/`

### 4.1 `config.py`

| 函数 | 签名 | 说明 |
|------|------|------|
| `load_config(config_path?)` | → Dict | 加载 YAML 配置 |
| `get_neo4j_config(config?)` | → Dict | 取 neo4j 配置 |
| `get_llm_config(config?)` | → Dict | 取 llm 配置 |
| `get_data_sources_config(config?)` | → Dict | 取 data_sources |
| `get_project_root()` | → Path | 项目根目录 |

### 4.2 `logger.py`

| 函数 | 签名 | 说明 |
|------|------|------|
| `get_logger(name, level?, format_string?, stream?)` | → Logger | 具名 logger |
| `setup_root_logger(level?, log_file?)` | 无返 | 配置根 logger |

---

## 5. 前端 `frontend/streamlit_app.py`

| 函数 | 说明 |
|------|------|
| `call_qa_api(question, max_hops?, temperature?)` | 调用后端 POST /qa，返回 JSON 或 None |
| `render_sidebar()` | 侧边栏（API 地址、参数） |
| `render_main()` | 主区域：输入框、提交、答案展示 |
| `main()` | 应用入口 |

---

## 6. 调用链（问答流程）

1. **API** `POST /qa` 接收 `question`
2. **QueryUnderstanding.parse(question)** → 得到 `entities`、`intent`
3. **GraphRetriever.retrieve_subgraph(entities)** → `SubGraphResult`
4. **GraphRetriever.subgraph_to_text(result)** → `graph_context`
5. **build_qa_prompt(graph_context, question)** → 完整 prompt
6. **LLMIntegration.generate(prompt, ...)** → `answer`
7. 组装 **QAResponse** 返回

各模块按上述接口实现即可串联成完整问答流水线。
