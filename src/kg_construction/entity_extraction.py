# 实体抽取：基于 HanLP/BERT-NER 的实体与关系抽取
from typing import List, Dict, Any, Tuple, Optional


# 三元组：(头实体, 关系, 尾实体) 或 (头实体名, 关系类型, 尾实体名)
Triple = Tuple[str, str, str]


class EntityExtractor:
    """实体与关系抽取器：从文本/结构化数据中抽取实体和三元组。"""

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any):
        """
        Args:
            model_name: NER/RE 模型名称或路径（如 HanLP、BERT-NER）。
            **kwargs: 其他模型或 pipeline 参数。
        """
        self.model_name = model_name
        self._model = None  # 懒加载

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        从单段文本中抽取实体。
        Args:
            text: 输入文本。
        Returns:
            实体列表，每项含 type, name, span 等字段。
        """
        raise NotImplementedError

    def extract_entities_batch(self, texts: List[str]) -> List[List[Dict[str, Any]]]:
        """批量抽取实体。"""
        raise NotImplementedError

    def extract_triples_from_text(self, text: str) -> List[Triple]:
        """
        从文本中抽取关系三元组 (头实体, 关系, 尾实体)。
        Args:
            text: 输入文本。
        Returns:
            三元组列表。
        """
        raise NotImplementedError

    def extract_triples_from_records(
        self, records: List[Dict[str, Any]], schema: Dict[str, List[Tuple[str, str, str]]]
    ) -> List[Triple]:
        """
        从结构化记录（如 DataFrame 行）按 schema 生成三元组。
        Args:
            records: 记录列表，每项为 dict。
            schema: 字段到 (头类型, 关系, 尾类型) 的映射或规则。
        Returns:
            三元组列表。
        """
        raise NotImplementedError
