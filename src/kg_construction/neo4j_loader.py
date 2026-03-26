import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any
from neo4j import GraphDatabase

from src.utils.config_loader import config, get_project_root
from src.utils.logger import logger

class Neo4jLoader:
    def __init__(self):
        self.uri = config.get("neo4j", {}).get("uri", "bolt://localhost:7687")
        self.username = config.get("neo4j", {}).get("username", "neo4j")
        self.password = config.get("neo4j", {}).get("password", "password")
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password), max_connection_lifetime=600, keep_alive=True)
            self.verify_connection()
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.error("Please check your Neo4j credentials in config.yaml or environment variables.")
            raise

    def clear_database(self):
        """清空数据库中的所有节点和关系（慎用）"""
        logger.warning("Clearing entire database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared.")

    def verify_connection(self):
        with self.driver.session() as session:
            session.run("RETURN 1")

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed.")

    def create_constraints(self):
        """创建唯一性约束，确保节点名称唯一"""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Disease) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Drug) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Symptom) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:NursingHome) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Insurance) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Department) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Population) REQUIRE n.name IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            for query in constraints:
                try:
                    session.run(query)
                    logger.info(f"Constraint created/verified: {query}")
                except Exception as e:
                    logger.warning(f"Failed to create constraint: {e}")

    def load_all(self):
        """执行所有数据加载任务"""
        self.clear_database()  # 根据用户要求，先清空数据库
        self.create_constraints()
        
        project_root = get_project_root()
        data_cleaned_dir = project_root / "DataCleaned"
        
        if not data_cleaned_dir.exists():
            logger.error(f"Data directory not found: {data_cleaned_dir}")
            return

        self._load_diseases(data_cleaned_dir / "Diseases" / "diseases.json")
        self._load_drugs(data_cleaned_dir / "Drugs" / "medicine.json")
        self._load_nursing_homes(data_cleaned_dir / "NursingHomes" / "nursing_homes.csv")
        self._load_insurances(data_cleaned_dir / "Insurance" / "insurance_info.json")

    def _load_diseases(self, file_path: Path):
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        logger.info(f"Loading diseases from {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 预处理数据
        processed_data = []
        for item in data:
            # 提取主要属性
            props = {
                "name": item.get("name"),
                "icd_code": item.get("icd_code"),
                "intro": item.get("intro"),
                "get_prob": item.get("get_prob"),
                "easy_get": item.get("easy_get"),
                "get_way": item.get("get_way"),
                "cause": item.get("cause"),
                "prevent": item.get("prevent"),
                "nursing": item.get("nursing"),
                "treat_detail": item.get("treat_detail")
            }
            
            # 提取关系数据
            symptoms = item.get("symptom", [])
            drugs = item.get("drug", [])
            neopathy = item.get("neopathy", [])
            dept = item.get("cure_dept", "").strip()
            
            processed_data.append({
                "props": props,
                "symptoms": symptoms,
                "drugs": drugs,
                "neopathy": neopathy,
                "dept": dept
            })

        # 批量写入
        query = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.props.name})
        SET d += row.props
        
        // Disease -> Symptom
        FOREACH (s_name IN row.symptoms | 
            MERGE (s:Symptom {name: s_name})
            MERGE (d)-[:HAS_SYMPTOM]->(s)
        )
        
        // Disease -> Department
        FOREACH (ignore IN CASE WHEN row.dept <> "" THEN [1] ELSE [] END |
            MERGE (dept:Department {name: row.dept})
            MERGE (d)-[:BELONGS_TO_DEPT]->(dept)
        )
        
        // Disease -> Drug (TREATED_BY)
        FOREACH (d_name IN row.drugs |
            MERGE (dg:Drug {name: d_name})
            MERGE (d)-[:TREATED_BY]->(dg)
        )
        
        // Disease -> Disease (Complication)
        FOREACH (n_name IN row.neopathy |
            MERGE (nd:Disease {name: n_name})
            MERGE (d)-[:HAS_COMPLICATION]->(nd)
        )
        """
        
        self._batch_run(query, processed_data, "Diseases")

    def _load_drugs(self, file_path: Path):
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        logger.info(f"Loading medicines from {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        processed_data = []
        # medicine.json 结构： {"西药部分": {"medicines": [...]}, ...}
        for category_name, content in data.items():
            medicines = content.get("medicines", [])
            for med in medicines:
                props = {
                    "name": med.get("name"),
                    "category_code": med.get("category_code"),
                    "subcategory_name": med.get("subcategory_name"),
                    "dosage": med.get("dosage"),
                    "reimbursement_category": med.get("reimbursement_category")
                }
                processed_data.append(props)

        query = """
        UNWIND $batch AS row
        MERGE (d:Drug {name: row.name})
        SET d += row
        """
        
        self._batch_run(query, processed_data, "Drugs")

    def _load_nursing_homes(self, file_path: Path):
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        logger.info(f"Loading nursing homes from {file_path}...")
        processed_data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("名称")
                if not name or not name.strip():
                    continue

                # 映射 CSV 列名到英文属性
                props = {
                    "name": name.strip(),
                    "city": row.get("城市"),
                    "nature": row.get("性质"),
                    "beds": row.get("床位"),
                    "price": row.get("价格(元/月)"),
                    "address": row.get("地址"),
                    "services": row.get("特色服务")
                }
                processed_data.append(props)

        query = """
        UNWIND $batch AS row
        MERGE (n:NursingHome {name: row.name})
        SET n += row
        """
        
        self._batch_run(query, processed_data, "NursingHomes")

    def _load_insurances(self, file_path: Path):
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        logger.info(f"Loading insurance info from {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        processed_data = []
        for item in data:
            props = {
                "name": item.get("产品名称"),
                "category": item.get("险种分类"),
                "company": item.get("承保公司"),
                "age_limit": item.get("承保年龄"),
                "duration": item.get("保障期限"),
                "price_desc": item.get("价格"),
                "description": item.get("产品描述", "")
            }
            processed_data.append(props)

        # 尝试建立简单的跨域关联
        # 1. 如果承保年龄包含 "老年" 或 "60" 以上，关联到 Population(老年人)
        # 2. 如果描述中包含常见慢性病（如高血压、糖尿病），关联到 Disease
        
        query = """
        UNWIND $batch AS row
        MERGE (i:Insurance {name: row.name})
        SET i += row
        
        // Link to Population
        FOREACH (ignore IN CASE WHEN row.age_limit CONTAINS '老年' OR row.age_limit CONTAINS '60' THEN [1] ELSE [] END |
            MERGE (p:Population {name: '老年人'})
            MERGE (i)-[:TARGETS_POPULATION]->(p)
        )
        
        // Simple Link to common diseases based on description
        FOREACH (ignore IN CASE WHEN row.description CONTAINS '高血压' THEN [1] ELSE [] END |
            MERGE (d:Disease {name: '高血压'})
            MERGE (i)-[:COVERS_DISEASE]->(d)
        )
        FOREACH (ignore IN CASE WHEN row.description CONTAINS '糖尿病' THEN [1] ELSE [] END |
            MERGE (d:Disease {name: '糖尿病'})
            MERGE (i)-[:COVERS_DISEASE]->(d)
        )
         FOREACH (ignore IN CASE WHEN row.description CONTAINS '癌症' OR row.description CONTAINS '恶性肿瘤' THEN [1] ELSE [] END |
            MERGE (d:Disease {name: '恶性肿瘤'}) // 假设有一个通用节点，或者这里只是简单示例
            MERGE (i)-[:COVERS_DISEASE]->(d)
        )
        """
        
        self._batch_run(query, processed_data, "Insurances")

    def _batch_run(self, query, data, label, batch_size=1000):
        total = len(data)
        logger.info(f"Starting import for {label}. Total records: {total}")
        
        with self.driver.session() as session:
            for i in range(0, total, batch_size):
                batch = data[i:i + batch_size]
                try:
                    session.run(query, batch=batch)
                    logger.info(f"Imported {label}: {min(i + batch_size, total)}/{total}")
                except Exception as e:
                    logger.error(f"Error importing batch {i//batch_size} for {label}: {e}")
        
        logger.info(f"Finished importing {label}")

if __name__ == "__main__":
    loader = Neo4jLoader()
    try:
        loader.load_all()
    finally:
        loader.close()
