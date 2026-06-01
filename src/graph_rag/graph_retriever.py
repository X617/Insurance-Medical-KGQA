
import os
from neo4j import GraphDatabase
from src.utils.config_loader import config
from src.utils.logger import logger
from src.graph_rag.recommendation_utils import (
    build_suitable_reason,
    insurance_risk_tags,
    normalize_city,
    parse_age_range,
    parse_price_value,
    score_insurance,
    score_nursing_home,
)
from src.graph_rag.lightweight_vector_index import LightweightVectorIndex

class GraphRetriever:
    def __init__(self):
        self.uri = config.get("neo4j", {}).get("uri", "bolt://localhost:7687")
        self.username = config.get("neo4j", {}).get("username", "neo4j")
        self.password = config.get("neo4j", {}).get("password", "password") or os.getenv("NEO4J_PASSWORD")
        self.database = config.get("neo4j", {}).get("database") or os.getenv("NEO4J_DATABASE")
        self.vector_index = LightweightVectorIndex()
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                connection_timeout=3,
                max_connection_pool_size=10,
                max_transaction_retry_time=1,
            )
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def get_graph_stats(self) -> dict:
        if not self.driver:
            return {"connected": False, "labels": {}, "relationships": 0}
        try:
            with self.driver.session(database=self.database) as session:
                labels = {
                    row["label"]: row["cnt"]
                    for row in session.run(
                        """
                        MATCH (n)
                        UNWIND labels(n) AS label
                        RETURN label, count(*) AS cnt
                        ORDER BY cnt DESC
                        """
                    )
                }
                rels = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
            return {"connected": True, "labels": labels, "relationships": rels}
        except Exception as exc:
            return {"connected": False, "labels": {}, "relationships": 0, "error": str(exc)}

    def _path_cards_from_strings(self, paths: list) -> list:
        cards = []
        for idx, path in enumerate(paths[:8], start=1):
            parts = [part.strip() for part in str(path).split("->") if part.strip()]
            cards.append({
                "title": f"证据路径 {idx}",
                "path": parts or [str(path)],
                "evidence": str(path),
                "score": round(max(0.52, 0.92 - idx * 0.04), 2),
            })
        return cards

    def get_subgraph(self, entity: str = "", query: str = "", depth: int = 1, limit: int = 40) -> dict:
        if not self.driver:
            return {"nodes": [], "edges": [], "paths": [], "message": "Database connection unavailable."}

        seed = (entity or query or "").strip()
        if not seed:
            return {"nodes": [], "edges": [], "paths": [], "message": "Missing entity or query."}

        depth = max(1, min(int(depth or 1), 4))
        limit = max(8, min(int(limit or 40), 180))
        cypher = f"""
        MATCH (start)
        WHERE start.name CONTAINS $seed OR $seed CONTAINS start.name
        WITH start LIMIT 5
        MATCH path=(start)-[*0..{depth}]-(n)
        WITH path LIMIT $limit
        RETURN path
        """

        nodes = {}
        edges = {}
        paths = []
        start_ids = set()
        with self.driver.session(database=self.database) as session:
            for row in session.run(cypher, seed=seed, limit=limit):
                path = row["path"]
                names = []
                for idx, node in enumerate(path.nodes):
                    node_id = str(node.element_id)
                    if idx == 0:
                        start_ids.add(node_id)
                    props = dict(node)
                    label = next(iter(node.labels), "Entity")
                    nodes[node_id] = {
                        "id": node_id,
                        "label": label,
                        "name": props.get("name", node_id),
                        "properties": props,
                        "seed": node_id in start_ids,
                    }
                    names.append(props.get("name", label))
                for rel in path.relationships:
                    rel_id = str(rel.element_id)
                    edges[rel_id] = {
                        "id": rel_id,
                        "source": str(rel.start_node.element_id),
                        "target": str(rel.end_node.element_id),
                        "type": rel.type,
                        "properties": dict(rel),
                    }
                if len(names) >= 2:
                    paths.append(" -> ".join(names))

        degree = {node_id: 0 for node_id in nodes}
        for edge in edges.values():
            degree[edge["source"]] = degree.get(edge["source"], 0) + 1
            degree[edge["target"]] = degree.get(edge["target"], 0) + 1
        for node_id, node in nodes.items():
            node["degree"] = degree.get(node_id, 0)
            node["size"] = min(34, 12 + node["degree"] * 2 + (8 if node.get("seed") else 0))

        return {
            "nodes": sorted(nodes.values(), key=lambda item: (not item.get("seed"), -item.get("degree", 0), item.get("name", ""))),
            "edges": list(edges.values()),
            "paths": paths[:10],
            "reasoning_paths": self._path_cards_from_strings(paths),
            "meta": {
                "seed": seed,
                "depth": depth,
                "limit": limit,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "start_count": len(start_ids),
            },
        }

    def _fallback_keyword_sources(self, raw_query: str, limit: int = 5) -> list:
        """Lightweight lexical recall used as a CPU-only HybridRAG fallback."""
        if not raw_query or not self.driver:
            return []
        keywords = [kw for kw in ["高血压", "糖尿病", "癌症", "医疗", "重疾", "防癌", "养老", "护理", "北京", "上海", "成都"] if kw in raw_query]
        if not keywords:
            keywords = [raw_query[:8]]
        with self.driver.session(database=self.database) as session:
            rows = session.run(
                """
                MATCH (n)
                WHERE any(kw IN $keywords WHERE
                    coalesce(n.name, '') CONTAINS kw OR
                    coalesce(n.description, '') CONTAINS kw OR
                    coalesce(n.intro, '') CONTAINS kw OR
                    coalesce(n.services, '') CONTAINS kw
                )
                RETURN labels(n)[0] AS label, n.name AS name,
                       coalesce(n.description, n.intro, n.services, n.address, '') AS text
                LIMIT $limit
                """,
                keywords=keywords,
                limit=limit,
            )
            return [
                {
                    "type": "hybrid_keyword",
                    "label": r["label"],
                    "name": r["name"],
                    "snippet": (r["text"] or "")[:160],
                    "score": 0.62,
                    "rule_score": 0.45,
                    "graph_score": 0.0,
                    "vector_score": 0.0,
                    "hybrid_score": 0.09,
                }
                for r in rows
            ]

    def _normalize_source_scores(self, source: dict, graph_score: float = 0.0, vector_score: float = 0.0, rule_score: float = 0.0) -> dict:
        source = dict(source)
        source["graph_score"] = round(float(source.get("graph_score", graph_score) or 0.0), 4)
        source["vector_score"] = round(float(source.get("vector_score", vector_score) or 0.0), 4)
        source["rule_score"] = round(float(source.get("rule_score", rule_score) or 0.0), 4)
        source["hybrid_score"] = round(
            0.45 * source["graph_score"] + 0.35 * source["vector_score"] + 0.20 * source["rule_score"],
            4,
        )
        source["score"] = source.get("hybrid_score") or source.get("score") or 0.0
        return source

    def _build_reasoning_paths(self, parsed_query: dict, payload: dict) -> list:
        age = parsed_query.get("age")
        diseases = parsed_query.get("disease") or []
        if isinstance(diseases, str):
            diseases = [diseases]
        city = normalize_city(parsed_query.get("city"))
        price_max = parsed_query.get("price_max")
        paths = []
        for item in (payload.get("recommendations", {}).get("insurance") or [])[:5]:
            seed = diseases[0] if diseases else (f"{age}岁用户" if age else "用户画像")
            paths.append({
                "title": item.get("name", "保险候选"),
                "path": [seed, "年龄/险种硬规则过滤", item.get("name", "保险候选")],
                "evidence": item.get("suitable_reason", ""),
                "score": item.get("score"),
            })
        for item in (payload.get("recommendations", {}).get("nursing_homes") or [])[:5]:
            seed = " / ".join(str(x) for x in [city, f"{price_max}元以内" if price_max else None] if x) or "养老需求"
            paths.append({
                "title": item.get("name", "养老机构候选"),
                "path": [seed, "城市/预算/服务能力过滤", item.get("name", "养老机构候选")],
                "evidence": f"{item.get('address', '')} {item.get('services', '')}"[:160],
                "score": item.get("score"),
            })
        if not paths:
            paths = self._path_cards_from_strings(payload.get("graph", {}).get("paths", []))
        return paths[:8]

    def retrieve_structured(self, parsed_query: dict) -> dict:
        context = self.retrieve(parsed_query)
        payload = getattr(self, "_last_payload", {}) or {}
        payload.setdefault("context", context)
        payload.setdefault("sources", [])
        payload.setdefault("recommendations", {"insurance": [], "nursing_homes": []})
        payload.setdefault("graph", {"nodes": [], "edges": [], "paths": []})

        raw_query = parsed_query.get("raw_query", "")
        hyde_query = parsed_query.get("hyde_query", "")
        vector_query = "\n".join(part for part in [raw_query, hyde_query] if part).strip()
        existing = {(s.get("label"), s.get("name")) for s in payload["sources"]}
        payload["sources"] = [
            self._normalize_source_scores(
                src,
                graph_score=float(src.get("score", 0.75) or 0.75),
                rule_score=0.65 if src.get("label") in {"Insurance", "NursingHome"} else 0.35,
            )
            for src in payload["sources"]
        ]
        for src in self.vector_index.search(vector_query or raw_query, top_k=5):
            key = (src.get("label"), src.get("name"))
            if key not in existing:
                src["retrieval_stage"] = "hyde_vector" if hyde_query else "vector"
                payload["sources"].append(self._normalize_source_scores(src))
                existing.add(key)
        for src in self._fallback_keyword_sources(raw_query):
            key = (src.get("label"), src.get("name"))
            if key not in existing:
                payload["sources"].append(self._normalize_source_scores(src, rule_score=0.45))
                existing.add(key)
        payload["sources"].sort(key=lambda item: item.get("hybrid_score", item.get("score", 0)), reverse=True)
        payload["sources"] = payload["sources"][:14]
        payload["reasoning_paths"] = self._build_reasoning_paths(parsed_query, payload)
        payload["graph"]["reasoning_paths"] = payload["reasoning_paths"]

        return payload

    def augment_with_drift(self, payload: dict, drift_queries: list, top_k: int = 3) -> tuple[dict, int]:
        """Run local DRIFT-style second-pass semantic probes and fuse evidence."""
        if not drift_queries:
            return payload, 0
        payload = dict(payload)
        payload.setdefault("sources", [])
        existing = {(s.get("label"), s.get("name")) for s in payload["sources"]}
        added = 0
        drift_context = []
        for drift_query in drift_queries[:3]:
            hits = self.vector_index.search(drift_query, top_k=top_k)
            if not hits:
                hits = self._fallback_keyword_sources(drift_query, limit=top_k)
            for src in hits:
                key = (src.get("label"), src.get("name"))
                if key in existing:
                    continue
                src = dict(src)
                src["retrieval_stage"] = "drift"
                src["drift_query"] = drift_query
                normalized = self._normalize_source_scores(
                    src,
                    graph_score=float(src.get("graph_score", 0.0) or 0.0),
                    vector_score=float(src.get("vector_score", src.get("score", 0.45)) or 0.45),
                    rule_score=float(src.get("rule_score", 0.35) or 0.35),
                )
                payload["sources"].append(normalized)
                existing.add(key)
                added += 1
                drift_context.append(
                    f"【DRIFT补充】{normalized.get('label')} · {normalized.get('name')}："
                    f"{str(normalized.get('snippet', ''))[:180]}"
                )
        payload["sources"].sort(key=lambda item: item.get("hybrid_score", item.get("score", 0)), reverse=True)
        payload["sources"] = payload["sources"][:16]
        if drift_context:
            payload["context"] = (payload.get("context") or "") + "\n\n【DRIFT 局部追问补充证据】\n" + "\n".join(drift_context[:6])
        return payload, added

    def retrieve(self, parsed_query: dict) -> str:
        """
        根据解析后的查询意图和关键词，在 Neo4j 中检索相关子图，
        并返回格式化的 Context 文本。
        """
        if not self.driver:
            return "Error: Database connection unavailable."

        context_parts = []
        sources = []
        graph_nodes = {}
        graph_edges = {}
        graph_paths = []
        recommendations = {"insurance": [], "nursing_homes": []}
        intent = parsed_query.get("intent", "general_qa")
        diseases = parsed_query.get("disease", [])
        drugs = parsed_query.get("drug", [])
        age = parsed_query.get("age")
        if isinstance(diseases, str):
            diseases = [diseases]
        if isinstance(drugs, str):
            drugs = [drugs]
        if isinstance(age, str) and age.isdigit():
            age = int(age)
        
        # === 修改点 1: 获取解析出的城市和价格上限 ===
        city = normalize_city(parsed_query.get("city"))
        price_max = parsed_query.get("price_max") 
        if isinstance(price_max, str):
            digits = "".join(ch for ch in price_max if ch.isdigit())
            price_max = int(digits) if digits else None

        def add_node(label, name, properties=None):
            if not name:
                return None
            node_id = f"{label}:{name}"
            graph_nodes[node_id] = {
                "id": node_id,
                "label": label,
                "name": name,
                "properties": properties or {},
            }
            return node_id

        def add_edge(source, target, rel_type, properties=None):
            if not source or not target:
                return
            edge_id = f"{source}->{rel_type}->{target}"
            graph_edges[edge_id] = {
                "id": edge_id,
                "source": source,
                "target": target,
                "type": rel_type,
                "properties": properties or {},
            }
        
        with self.driver.session(database=self.database) as session:
            
            # 1. 疾病相关检索 (并发症、药品、保险)
            if diseases:
                for disease_name in diseases:
                    # 检索疾病基本信息、并发症、药品
                    cypher_disease = """
                    MATCH (d:Disease {name: $name})
                    OPTIONAL MATCH (d)-[:HAS_COMPLICATION]->(c:Disease)
                    OPTIONAL MATCH (d)-[:TREATED_BY]->(m:Drug)
                    OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
                    RETURN d, collect(DISTINCT c.name) as complications, 
                           collect(DISTINCT m.name) as drugs,
                           collect(DISTINCT s.name) as symptoms
                    """
                    result = session.run(cypher_disease, name=disease_name).single()
                    
                    if result:
                        d_node = result['d']
                        complications = result['complications']
                        drug_list = result['drugs']
                        symptom_list = result['symptoms']
                        
                        info = f"【疾病信息】{disease_name}:\n"
                        if d_node.get('intro'):
                            info += f"  - 简介: {d_node.get('intro')}\n"
                        if d_node.get('treat_detail'):
                            info += f"  - 治疗: {d_node.get('treat_detail')}\n"
                        if symptom_list:
                            info += f"  - 症状: {', '.join(symptom_list[:5])}\n"
                        if complications:
                            info += f"  - 并发症: {', '.join(complications[:5])}\n"
                        if drug_list:
                            info += f"  - 常用药物: {', '.join(drug_list[:5])}\n"
                        context_parts.append(info)
                        d_id = add_node("Disease", disease_name, dict(d_node))
                        sources.append({"type": "graph", "label": "Disease", "name": disease_name, "snippet": info[:180], "score": 0.95})
                        for symptom in symptom_list[:5]:
                            s_id = add_node("Symptom", symptom)
                            add_edge(d_id, s_id, "HAS_SYMPTOM")
                        for drug_name in drug_list[:5]:
                            m_id = add_node("Drug", drug_name)
                            add_edge(d_id, m_id, "TREATED_BY")

                    # 检索覆盖该疾病的保险
                    cypher_insurance = """
                    MATCH (i:Insurance)-[:COVERS_DISEASE]->(d:Disease {name: $name})
                    RETURN i.name as ins_name, i.description as desc, i.age_limit as age_limit
                    """
                    ins_results = session.run(cypher_insurance, name=disease_name)
                    ins_list = [f"{r['ins_name']} (年龄限制: {r['age_limit']})" for r in ins_results]
                    
                    if ins_list:
                        context_parts.append(f"【推荐保险】针对 {disease_name} 的相关保险产品: {', '.join(ins_list)}")

            # 2. 年龄相关保险检索
            if age:
                if age >= 60:
                    cypher_age = """
                    MATCH (i:Insurance)-[:TARGETS_POPULATION]->(p:Population {name: '老年人'})
                    RETURN i.name as ins_name, i.age_limit as age_limit, i.description as desc
                    LIMIT 5
                    """
                    age_results = session.run(cypher_age)
                    rec_ins = []
                    for r in age_results:
                        rec_ins.append(f"{r['ins_name']} ({r['age_limit']})")
                    
                    if rec_ins:
                        context_parts.append(f"【适老保险】适合 {age} 岁人群的保险产品: {', '.join(rec_ins)}")

# ... (保留上面的疾病和年龄检索代码) ...

            # ==========================================
            # === 修改点：增强版保险精准检索逻辑 ===
            # ==========================================
            # ==========================================
            # === 修改后的保险检索逻辑：优先关键词匹配 ===
            # ==========================================
            if intent == "insurance_query":
                # 1. 获取原始问题文本
                raw_query = parsed_query.get("raw_query", "")
                
                # 2. 动态构建 Cypher 查询
                # 逻辑：如果问题里包含具体的系列名（如"蓝医保"），就优先搜它
                # 否则才去搜泛泛的"医疗"、"重疾"
                
                specific_keyword = ""
                # 这里可以根据你的业务数据扩展常见系列名
                known_series = ["蓝医保", "好医保", "金医保", "平安", "众安", "长相安"]
                for series in known_series:
                    if series in raw_query:
                        specific_keyword = series
                        break
                
                if specific_keyword:
                    # === 场景 A: 精准狙击 ===
                    # 用户提到了具体系列，直接 CONTAINS 那个系列名
                    logger.info(f"🔍 检测到特定产品系列: {specific_keyword}，执行精准检索")
                    cypher_ins = f"""
                    MATCH (i:Insurance)
                    WHERE i.name CONTAINS '{specific_keyword}'
                    RETURN i.name as name, 
                           i.age_limit as age_limit, 
                           i.description as desc,
                           i.category as category,
                           i.price as price
                    LIMIT 6  // 精准搜索时 LIMIT 可以大一点，确保该系列全覆盖
                    """
                else:
                    # === 场景 B: 泛泛搜索 (保留原有逻辑) ===
                    # 用户只说了"推荐个保险"，那就随机推荐
                    logger.info("🔍 未检测到特定系列，执行通用随机检索")
                    cypher_ins = """
                    MATCH (i:Insurance)
                    WHERE i.name CONTAINS '重疾' OR i.name CONTAINS '医疗' OR i.name CONTAINS '护理' OR i.name CONTAINS '防癌'
                    RETURN i.name as name, 
                           i.age_limit as age_limit, 
                           i.description as desc,
                           i.category as category,
                           i.price as price
                    ORDER BY rand()
                    LIMIT 20
                    """

                # 执行查询
                gen_results = session.run(cypher_ins)
                
                ins_data = []
                for r in gen_results:
                    min_age, max_age = parse_age_range(r["age_limit"])
                    tags = insurance_risk_tags(r["name"], r.get("category", ""), r["desc"] or "")
                    ins_data.append({
                        "name": r['name'],
                        "category": r.get('category', '未知'),
                        "age_limit": r['age_limit'],
                        "description": r['desc'] or "",
                        "price": r.get("price"),
                        "price_value": parse_price_value(r.get("price")),
                        "min_age": min_age,
                        "max_age": max_age,
                        "risk_tags": tags,
                    })

                for item in ins_data:
                    item["score"] = score_insurance(item, age, diseases, raw_query)
                    item["suitable_reason"] = build_suitable_reason(item, age, diseases)

                ins_data = [item for item in ins_data if item["score"] > -999]
                ins_data.sort(key=lambda x: x["score"], reverse=True)
                recommendations["insurance"] = ins_data[:6]
                
                # 格式化输出给 LLM
                filtered_ins_list = []
                for item in recommendations["insurance"]:
                    item_str = f"【产品】{item['name']}\n   - 险种: {item['category']}\n   - 投保年龄: {item['age_limit']}\n   - 推荐分: {item['score']}\n   - 推荐理由: {item['suitable_reason']}\n   - 描述: {item['description'][:80]}..."
                    filtered_ins_list.append(item_str)
                    ins_id = add_node("Insurance", item["name"], item)
                    sources.append({"type": "graph", "label": "Insurance", "name": item["name"], "snippet": item_str, "score": item["score"] / 100})
                    if age is not None:
                        pop_id = add_node("Population", f"{age}岁用户", {"age": age})
                        add_edge(ins_id, pop_id, "AGE_MATCH")
                    for disease_name in diseases or []:
                        d_id = add_node("Disease", disease_name)
                        add_edge(ins_id, d_id, "RELATED_TO_DISEASE")
                        graph_paths.append(f"{disease_name} -> RELATED_TO_DISEASE -> {item['name']}")
                
                if filtered_ins_list:
                    context_parts.append(f"【保险产品库】(已根据关键词 '{specific_keyword or '通用'}' 筛选):\n" + "\n".join(filtered_ins_list))
             
            
            # === 修改点 2: 修复养老院检索逻辑 ===
            # 只要意图是找养老院，或者查询中包含了城市/价格，就触发检索
            if intent == "nursing_home_search" or city or price_max:
                params = {}
                # 基础查询
                query_parts = ["MATCH (n:NursingHome)"]
                where_clauses = []
                
                # 逻辑修复：如果在找城市，去 'address' 或 'name' 里找，而不是不存在的 'city' 属性
                if city:
                    where_clauses.append("(n.address CONTAINS $city OR n.name CONTAINS $city)")
                    params['city'] = city
                
                # 逻辑修复：启用价格过滤，注意数据库里的 price 是字符串，需要转数字
                if price_max:
                    where_clauses.append("toInteger(n.price) <= $price_max")
                    params['price_max'] = price_max
                
                if where_clauses:
                    query_parts.append("WHERE " + " AND ".join(where_clauses))
                
                # 逻辑修复：RETURN 中删除了 n.city，改用 address
                query_parts.append("""
                    RETURN n.name as name, 
                           n.price as price, 
                           n.address as address, 
                           n.services as services, 
                           n.beds as beds, 
                           n.nature as nature 
                        LIMIT 5
                """)                
                nh_query = "\n".join(query_parts)
                logger.info(f"Executing Cypher: {nh_query} | Params: {params}") # 添加日志方便调试
                
                nh_results = session.run(nh_query, **params)
                
                nh_list = []
                for r in nh_results:
                    item = {
                        "name": r["name"],
                        "price": r["price"],
                        "price_value": parse_price_value(r["price"]),
                        "address": r["address"],
                        "services": r["services"],
                        "beds": r["beds"],
                        "nature": r["nature"],
                    }
                    item["score"] = score_nursing_home(item, city, price_max)
                    recommendations["nursing_homes"].append(item)
                    # 4. 【关键修改】构建详细的信息卡片，而不是简单的一句话
                    detail = f"【{r['name']}】"
                    detail += f"\n  - 价格: {r['price']}元/月"
                    detail += f"\n  - 地址: {r['address']}"
                    
                    # 使用 .get() 或检查 None，防止数据缺失时报错
                    if r['nature']:
                        detail += f"\n  - 性质: {r['nature']}"
                    if r['beds']:
                        detail += f"\n  - 床位: {r['beds']}"
                    if r['services']:
                        # 截取过长的服务描述，避免 Context 爆长
                        services = r['services'][:100] + "..." if len(str(r['services'])) > 100 else r['services']
                        detail += f"\n  - 特色服务: {services}"
                    
                    nh_list.append(detail)

                recommendations["nursing_homes"] = [
                    item for item in recommendations["nursing_homes"] if item["score"] > -999
                ]
                recommendations["nursing_homes"].sort(key=lambda x: x["score"], reverse=True)
                recommendations["nursing_homes"] = recommendations["nursing_homes"][:6]
                for item in recommendations["nursing_homes"]:
                    nh_id = add_node("NursingHome", item["name"], item)
                    sources.append({"type": "graph", "label": "NursingHome", "name": item["name"], "snippet": f"{item['address']}，{item['price']}元/月，{item['services']}", "score": item["score"] / 100})
                    if city:
                        city_id = add_node("City", city)
                        add_edge(nh_id, city_id, "LOCATED_IN")
                    if item.get("services"):
                        service_id = add_node("Service", "医养服务")
                        add_edge(nh_id, service_id, "PROVIDES")
                
                if nh_list:
                    # 将结构化的文本加入 context
                    context_str = f"【养老机构推荐】(筛选条件: 城市={city or '不限'}, 预算<{price_max or '不限'}):\n" + "\n".join(nh_list)
                    context_parts.append(context_str)
                else:
                    context_parts.append(f"【养老机构】未找到符合条件的养老院 (城市: {city}, 预算: {price_max})。")

        # === ！！！必须确保这下面有这两行代码！！！ ===
        self._last_payload = {
            "sources": sources[:12],
            "recommendations": recommendations,
            "graph": {
                "nodes": list(graph_nodes.values()),
                "edges": list(graph_edges.values()),
                "paths": graph_paths[:10],
            },
        }

        if not context_parts:
            self._last_payload["context"] = "知识图谱检索完成，但在图谱中未发现与该特定实体或条件直接匹配的记录。"
            return "知识图谱检索完成，但在图谱中未发现与该特定实体或条件直接匹配的记录。"
        
        self._last_payload["context"] = "\n".join(context_parts)
        return "\n".join(context_parts)  # <--- 这行丢失会导致报错！

if __name__ == "__main__":
    # 测试代码
    retriever = GraphRetriever()
    
    # 模拟 QueryParser 的输出
    mock_query = {
        "city": "北京",
        "price_max": 5000,
        "intent": "nursing_home_search"
    }
    
    context = retriever.retrieve(mock_query)
    print(context)
    
    retriever.close()
