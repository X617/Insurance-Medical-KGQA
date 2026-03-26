import os
import json
import re
from neo4j import GraphDatabase
from src.utils.logger import logger
from src.graph_rag.llm_integration import LLMIntegration
from src.utils.config_loader import config

class TextGraphBuilder:
    def __init__(self):
        # 1. 初始化 Neo4j 连接
        self.uri = config.get("neo4j", {}).get("uri", "bolt://localhost:7687")
        self.username = config.get("neo4j", {}).get("username", "neo4j")
        self.password = config.get("neo4j", {}).get("password", "password") or os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        
        # 2. 初始化 LLM
        self.llm = LLMIntegration()

    def close(self):
        self.driver.close()

    def extract_triples(self, text):
        """
        利用 LLM 从文本中提取三元组
        """
        logger.info("正在调用 LLM 进行信息抽取...")
        
        # === 核心 Prompt：定义 Schema ===
        prompt = f"""
        你是一个知识图谱构建专家。请从下面的【保险条款文本】中提取实体和关系，并以严格的 JSON 列表格式输出。

        【目标实体类型】:
        - Insurance (保险产品)
        - Disease (疾病)
        - AgeRange (年龄范围)
        - Exclusion (除外责任/拒保情形)

        【目标关系类型】:
        - COVERS (覆盖/保障)
        - EXCLUDES (不保/除外)
        - ALLOWS_AGE (投保年龄)
        - REFUSES_DISEASE (拒保疾病)

        【保险条款文本】:
        {text}

        【输出要求】:
        1. 仅输出 JSON 列表，不要包含 Markdown 标记（如 ```json）。
        2. 格式示例: 
        [
            {{"head": "产品名", "type": "Insurance", "relation": "COVERS", "tail": "疾病名", "tail_type": "Disease"}},
            {{"head": "产品名", "type": "Insurance", "relation": "ALLOWS_AGE", "tail": "0-65周岁", "tail_type": "AgeRange"}}
        ]
        """
        
        try:
            # 调用大模型
            response = self.llm.generate(prompt, temperature=0.1) # 低温度保证格式稳定
            
            # 清理可能的 Markdown 格式
            cleaned_response = response.replace("```json", "").replace("```", "").strip()
            triples = json.loads(cleaned_response)
            logger.info(f"成功提取 {len(triples)} 个三元组")
            return triples
        except Exception as e:
            logger.error(f"提取失败: {e}")
            logger.error(f"LLM 原始返回: {response}")
            return []

    def save_to_neo4j(self, triples):
        """
        将三元组写入 Neo4j
        """
        if not triples:
            return

        with self.driver.session() as session:
            for item in triples:
                try:
                    # 动态构建 Cypher (MERGE 防止重复)
                    # 注意：这里为了简化，我们假设 head 都是 Insurance 类型，实际可根据 item['type'] 动态调整
                    cypher = f"""
                    MERGE (h:{item['type']} {{name: $head_name}})
                    MERGE (t:{item['tail_type']} {{name: $tail_name}})
                    MERGE (h)-[:{item['relation']}]->(t)
                    """
                    session.run(cypher, head_name=item['head'], tail_name=item['tail'])
                    logger.info(f"写入图谱: ({item['head']}) -[{item['relation']}]-> ({item['tail']})")
                except Exception as e:
                    logger.error(f"写入 Neo4j 失败: {e}")

def main():
    # 读取文本文件
    file_path = "data/raw_text/sample_policy.txt"
    if not os.path.exists(file_path):
        logger.error(f"找不到文件: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        text_content = f.read()

    builder = TextGraphBuilder()
    try:
        # 1. 提取
        triples = builder.extract_triples(text_content)
        # 2. 写入
        builder.save_to_neo4j(triples)
        logger.info("=== 全部处理完成 ===")
    finally:
        builder.close()

if __name__ == "__main__":
    main()