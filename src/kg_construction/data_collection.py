# 数据收集：原始数据加载与路径配置
from pathlib import Path
from typing import Dict, List, Any, Optional


class DataCollector:
    """数据收集类：按配置加载医疗、保险等原始数据。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 数据源配置，含 medical / insurance 等 key，值为文件路径列表。
        """
        self.config = config or {}
        self._base_path: Optional[Path] = None

    def set_base_path(self, base_path: str) -> None:
        """设置项目根路径，后续路径均相对此路径解析。"""
        self._base_path = Path(base_path)

    def _resolve_path(self, path_str: str) -> Path:
        """将配置中的相对路径解析为绝对路径。"""
        p = Path(path_str)
        if not p.is_absolute() and self._base_path is not None:
            p = self._base_path / p
        return p

    def get_medical_sources(self) -> List[str]:
        """返回医疗数据源路径列表（如 icd_codes.csv, drugbank.json）。"""
        return self.config.get("medical", [])

    def get_insurance_sources(self) -> List[str]:
        """返回保险数据源路径列表。"""
        return self.config.get("insurance", [])

    def load_medical(self) -> Dict[str, Any]:
        """
        加载所有医疗相关原始数据。
        Returns:
            键为数据源标识，值为 DataFrame 或 dict/list（如 JSON）。
        """
        raise NotImplementedError

    def load_insurance(self) -> Dict[str, Any]:
        """
        加载所有保险相关原始数据。
        Returns:
            键为数据源标识，值为 DataFrame 或 dict/list。
        """
        raise NotImplementedError

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """
        加载全部配置的数据源。
        Returns:
            {"medical": {...}, "insurance": {...}}
        """
        raise NotImplementedError
