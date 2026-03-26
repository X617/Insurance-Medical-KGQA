import yaml
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

def get_project_root() -> Path:
    """
    获取项目根目录路径。
    """
    current_path = Path(__file__).resolve()
    for parent in [current_path] + list(current_path.parents):
        if (parent / "config.yaml").exists():
            return parent
    return current_path.parent.parent.parent

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置：优先使用环境变量 (.env)，其次使用 config.yaml。
    """
    if config_path:
        path = Path(config_path)
    else:
        root = get_project_root()
        path = root / "config.yaml"
        # 加载 .env 文件
        load_dotenv(root / ".env")
    
    config_data = {}
    
    # 1. 加载 config.yaml
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            try:
                file_config = yaml.safe_load(f) or {}
                config_data.update(file_config)
            except yaml.YAMLError as e:
                print(f"Warning: Failed to parse config.yaml: {e}")

    # 2. 环境变量覆盖 (Environment Variables Override)
    # 将平铺的环境变量映射回嵌套的 config 结构，或者直接更新顶层键
    
    # Neo4j
    if os.getenv("NEO4J_URI"):
        if "neo4j" not in config_data: config_data["neo4j"] = {}
        config_data["neo4j"]["uri"] = os.getenv("NEO4J_URI")
    if os.getenv("NEO4J_USERNAME"):
        if "neo4j" not in config_data: config_data["neo4j"] = {}
        config_data["neo4j"]["username"] = os.getenv("NEO4J_USERNAME")
    if os.getenv("NEO4J_PASSWORD"):
        if "neo4j" not in config_data: config_data["neo4j"] = {}
        config_data["neo4j"]["password"] = os.getenv("NEO4J_PASSWORD")
        
    # OpenAI / LLM
    if os.getenv("OPENAI_API_KEY"):
        config_data["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("OPENAI_BASE_URL"):
        config_data["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")

    return config_data

# 全局配置对象
try:
    config = load_config()
except Exception as e:
    print(f"Warning: Global config load failed: {e}")
    config = {}

if __name__ == "__main__":
    print(f"Project Root: {get_project_root()}")
    # 打印时隐藏敏感信息
    safe_config = config.copy()
    if "OPENAI_API_KEY" in safe_config:
        safe_config["OPENAI_API_KEY"] = "******"
    if "neo4j" in safe_config and "password" in safe_config["neo4j"]:
        safe_config["neo4j"]["password"] = "******"
    print(f"Loaded Config: {safe_config}")
