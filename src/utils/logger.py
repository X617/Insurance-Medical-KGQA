import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logger(name: str = "kg_qa", log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    创建一个简单的 logger 配置。
    
    Args:
        name: Logger 名称
        log_file: 日志文件路径（可选）。如果提供，日志也会输出到文件。
        level: 日志级别，默认为 INFO
    
    Returns:
        配置好的 logger 对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
        
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出（如果指定）
    if log_file:
        log_path = Path(log_file)
        # 确保日志目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

# 创建一个默认的全局 logger
# 默认不写入文件，如果需要写入文件，可以在主程序入口处重新调用 setup_logger 配置
logger = setup_logger()
