
import os
from neo4j import GraphDatabase
from src.utils.config_loader import config
from src.utils.logger import logger

class GraphRetriever:
    def __init__(self):
        self.uri = config.get("neo4j", {}).get("uri", "bolt://localhost:7687")
        self.username = config.get("neo4j", {}).get("username", "neo4j")
        self.password = config.get("neo4j", {}).get("password", "password")or os.getenv("NEO4J_PASSWORD")
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def retrieve(self, parsed_query: dict) -> str:
        """
        根据解析后的查询意图和关键词，在 Neo4j 中检索相关子图，
        并返回格式化的 Context 文本。
        """
        if not self.driver:
            return "Error: Database connection unavailable."

        context_parts = []
        intent = parsed_query.get("intent", "general_qa")
        diseases = parsed_query.get("disease", [])
        drugs = parsed_query.get("drug", [])
        age = parsed_query.get("age")
        
        # === 修改点 1: 获取解析出的城市和价格上限 ===
        city = parsed_query.get("city")
        price_max = parsed_query.get("price_max") 
        
        with self.driver.session() as session:
            
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
                    ins_data.append({
                        "name": r['name'],
                        "category": r.get('category', '未知'),
                        "age_limit": r['age_limit'],
                        "desc": r['desc']
                    })
                
                # 格式化输出给 LLM
                filtered_ins_list = []
                for item in ins_data:
                    item_str = f"【产品】{item['name']}\n   - 险种: {item['category']}\n   - 投保年龄: {item['age_limit']}\n   - 描述: {item['desc'][:50]}..."
                    filtered_ins_list.append(item_str)
                
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
                
                if nh_list:
                    # 将结构化的文本加入 context
                    context_str = f"【养老机构推荐】(筛选条件: 城市={city or '不限'}, 预算<{price_max or '不限'}):\n" + "\n".join(nh_list)
                    context_parts.append(context_str)
                else:
                    context_parts.append(f"【养老机构】未找到符合条件的养老院 (城市: {city}, 预算: {price_max})。")

        # === ！！！必须确保这下面有这两行代码！！！ ===
        if not context_parts:
            return "知识图谱检索完成，但在图谱中未发现与该特定实体或条件直接匹配的记录。"
        
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