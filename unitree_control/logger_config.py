import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = __name__, log_dir: str = "./logs") -> logging.Logger:
    """
    设置日志记录器，支持日志轮转
    
    Args:
        name: 记录器名称
        log_dir: 日志存储目录
        
    Returns:
        配置好的Logger对象
    """
    # 创建日志目录（如果不存在）
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 创建文件处理器（带轮转功能）
    log_file = log_path / "unitree_control.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 最大5MB
        backupCount=5,             # 最多保留5个文件
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# 全局日志记录器实例
logger = setup_logger("unitree_control")