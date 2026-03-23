"""
统一日志配置模块
实现日志文件大小限制和格式化输出功能
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


class LoggerManager:
    """
    日志管理器
    提供统一的日志记录功能，支持文件大小限制和格式化输出
    """
    
    def __init__(self, log_dir="logs", max_bytes=10*1024*1024, backup_count=5):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志文件存放目录
            max_bytes: 单个日志文件最大大小（字节），默认10MB
            backup_count: 保留的备份文件数量
        """
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置基本日志配置
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志配置"""
        # 创建日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        # 创建RotatingFileHandler，限制文件大小
        log_filename = os.path.join(
            self.log_dir, 
            f"g1_robot_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        file_handler = RotatingFileHandler(
            filename=log_filename,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # 设置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        
        # 添加控制台处理器（可选，也可以注释掉以仅保存到文件）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name):
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            logging.Logger: 日志记录器实例
        """
        return logging.getLogger(name)


# 全局日志管理器实例
logger_manager = LoggerManager()


def get_logger(name):
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logger_manager.get_logger(name)


def setup_ros2_logger(node):
    """
    为ROS2节点设置日志记录器
    
    Args:
        node: ROS2节点实例
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 使用节点名称作为日志记录器名称
    logger_name = node.get_name() if hasattr(node, 'get_name') else str(node.__class__.__name__)
    return get_logger(logger_name)