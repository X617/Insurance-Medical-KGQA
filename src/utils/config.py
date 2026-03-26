# 配置文件加载：统一读取 config.yaml 等
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def get_project_root() -> Path:
    """返回项目根目录（含 config.yaml 的目录）。"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config.yaml").exists():
            return parent
    return current.parent.parent.parent  # 默认 src/utils -> 项目根


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载 YAML 配置文件。
    Args:
        config_path: 配置文件路径，默认在项目根目录查找 config.yaml。
    Returns:
        配置字典，含 neo4j / llm / data_sources 等 key。
    """
    if yaml is None:
        raise RuntimeError("请安装 PyYAML: pip install pyyaml")
    path = Path(config_path) if config_path else (get_project_root() / "config.yaml")
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_neo4j_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    if config is None:
        config = load_config()
    return config.get("neo4j", {})


def get_llm_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if config is None:
        config = load_config()
    return config.get("llm", {})


def get_data_sources_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, list]:
    if config is None:
        config = load_config()
    return config.get("data_sources", {})
