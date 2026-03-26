"""
人脸图像缓存模块
提供全局的人脸图像缓存功能，支持按名称存储和检索人脸图像
"""
from collections import OrderedDict
from sensor_msgs.msg import Image
from threading import RLock

# 导入日志配置
from .logger_config import get_logger

# 全局人脸图像缓存实例
_global_face_image_cache = None
_cache_lock = RLock()  # 使用可重入锁确保线程安全

def get_face_image_cache():
    """
    获取全局人脸图像缓存实例
    
    Returns:
        FaceImageCache: 人脸图像缓存实例
    """
    global _global_face_image_cache
    if _global_face_image_cache is None:
        with _cache_lock:
            if _global_face_image_cache is None:  # double-check locking
                _global_face_image_cache = FaceImageCache()
    return _global_face_image_cache


class FaceImageCache:
    """
    人脸图像缓存类，提供按名称存储和检索人脸图像的功能
    """
    
    def __init__(self, max_cache_size=5):
        self.cache = OrderedDict()
        self.max_cache_size = max_cache_size
        self.logger = get_logger(self.__class__.__name__)
        self.lock = RLock()  # 使用可重入锁确保线程安全
    
    def store_face_image(self, name, image_msg):
        """
        将人脸图像存储到缓存中
        
        Args:
            name (str): 人脸名称
            image_msg (sensor_msgs.Image): 图像消息
        """
        with self.lock:
            # 如果缓存已满且没有当前名称的图像，则删除最旧的条目
            if name not in self.cache and len(self.cache) >= self.max_cache_size:
                # 删除最旧的条目（OrderedDict的第一个元素）
                oldest_name = next(iter(self.cache))
                del self.cache[oldest_name]
                self.logger.debug(f"Removed oldest face image from cache: {oldest_name}")
            
            # 存储当前人脸图像
            self.cache[name] = image_msg
            self.logger.debug(f"Stored face image in cache for: {name}, cache size: {len(self.cache)}")
    
    def get_face_image(self, name):
        """
        根据名称获取人脸图像
        
        Args:
            name (str): 人脸名称
            
        Returns:
            sensor_msgs.Image or None: 图像消息或None
        """
        with self.lock:
            self.logger.debug(f"从内存中获取 {name} 图像信息！现有：{self.cache.keys()}")
            return self.cache.get(name)
    
    def remove_face_image(self, name):
        """
        根据名称删除人脸图像
        
        Args:
            name (str): 人脸名称
            
        Returns:
            bool: 是否删除成功
        """
        with self.lock:
            if name in self.cache:
                del self.cache[name]
                self.logger.debug(f"Removed face image from cache for: {name}")
                return True
            return False
    
    def clear_cache(self):
        """
        清空整个缓存
        """
        with self.lock:
            self.cache.clear()
            self.logger.debug("Cleared face image cache")
    
    def get_cache_size(self):
        """
        获取当前缓存大小
        
        Returns:
            int: 缓存大小
        """
        with self.lock:
            return len(self.cache)
    
    def get_cached_names(self):
        """
        获取所有已缓存的人脸名称
        
        Returns:
            list: 人脸名称列表
        """
        with self.lock:
            return list(self.cache.keys())