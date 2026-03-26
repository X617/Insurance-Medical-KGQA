# 本体设计：实体类型与关系定义
from typing import Dict, List, Tuple, Any


class OntologyDesign:
    """本体设计类：定义知识图谱实体类型、属性及关系 schema。"""

    ENTITY_TYPES: Dict[str, List[str]] = {
        "Disease": ["name", "code", "category"],
        "Drug": ["name", "ingredient", "indication"],
        "InsuranceProduct": ["name", "company", "coverage"],
        "ElderlyService": ["name", "type", "location"],
        "AgeCondition": ["min_age", "max_age", "description"],
    }

    RELATIONSHIPS: List[Tuple[str, str, str]] = [
        ("Disease", "TREATED_BY", "Drug"),
        ("InsuranceProduct", "COVERS", "Disease"),
        ("InsuranceProduct", "HAS_AGE_LIMIT", "AgeCondition"),
        ("ElderlyService", "RELATED_TO", "Disease"),
    ]

    @classmethod
    def get_entity_types(cls) -> Dict[str, List[str]]:
        """返回所有实体类型及其属性列表。"""
        return cls.ENTITY_TYPES.copy()

    @classmethod
    def get_relationships(cls) -> List[Tuple[str, str, str]]:
        """返回 (头实体类型, 关系类型, 尾实体类型) 列表。"""
        return cls.RELATIONSHIPS.copy()

    @classmethod
    def get_entity_labels(cls) -> List[str]:
        """返回所有实体类型标签，用于 Neo4j 节点标签。"""
        return list(cls.ENTITY_TYPES.keys())

    @classmethod
    def get_schema_for_entity(cls, entity_type: str) -> List[str]:
        """返回指定实体类型的属性 schema，不存在则返回空列表。"""
        return cls.ENTITY_TYPES.get(entity_type, [])
