"""
图像上传工具模块
提供图像上传到云端图床的功能，并带有去重机制
"""
import json
import time
import threading
import requests
import tempfile
import os
import cv2
from cv_bridge import CvBridge
from collections import defaultdict

# 导入日志配置
from .logger_config import get_logger


class ImageUploader:
    """
    图像上传器，负责将图像上传到云端并提供去重功能
    """
    
    def __init__(self):
        # 企业微信机器人配置
        self.bot_id = "aibPK7lIHLBWw8DTawBKdyh1Q9cwXIqp29I"  # 请替换为实际的Bot ID
        self.secret = "DraM3GAPGWuGCeX50pDkasYXtnFiPsaIrjyNAh82xn7"  # 请替换为实际的Secret
        
        # Lsky Pro 图床配置
        self.lsky_base_url = "http://tiagent.tech:7791/api/v1"  # 使用域名
        self.lsky_email = "Nathan@Haitch.cn"  # Nathan账号
        self.lsky_password = "12345678"  # Nathan密码
        self.lsky_strategy_id = 1  # 强制使用策略ID 1

        # 图片压缩参数
        self.image_quality = 30  # 图片压缩质量（1-100）
        self.max_image_size = 480  # 图片最大边长（像素）
        
        # 记录每个人脸最后上传时间 (name -> (timestamp, url))
        self.upload_records = {}
        self.record_lock = threading.Lock()
        
        # 检查必要的库是否可用
        try:
            import requests
            self.requests_available = True
        except ImportError:
            self.requests_available = False
            logger = get_logger(__name__)
            logger.error("requests库未安装，请运行: pip install requests")
        
        self.logger = get_logger(self.__class__.__name__)
    
    def _get_lsky_token(self):
        """
        通过Nathan账号获取Lsky Pro的Token
        """
        if not self.requests_available:
            self.logger.error("requests库不可用，无法获取Token")
            return None

        try:
            url = f"{self.lsky_base_url}/tokens"
            data = {
                "email": self.lsky_email,
                "password": self.lsky_password
            }
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            self.logger.info(f"[上传] 正在使用Nathan账号登录获取Token...")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            result = response.json()

            if result.get("status") and result.get("data", {}).get("token"):
                token = result["data"]["token"]
                self.logger.info(f"[上传] 登录成功! Token: {token[:20]}...")
                return token
            else:
                message = result.get("message", "未知错误")
                self.logger.error(f"[上传] 登录失败: {message}")
                return None

        except Exception as e:
            self.logger.error(f"[上传] 获取Token异常: {e}")
            import traceback
            self.logger.error(f"[上传] 详细错误: {traceback.format_exc()}")
            return None
    
    def _compress_image(self, cv_image):
        """
        压缩图像
        """
        try:
            height, width = cv_image.shape[:2]
            max_size = self.max_image_size

            if max(height, width) > max_size:
                if height > width:
                    new_height = max_size
                    new_width = int(width * max_size / height)
                else:
                    new_width = max_size
                    new_height = int(height * max_size / width)

                cv_image = cv2.resize(cv_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            return cv_image
        except Exception as e:
            self.logger.error(f"图像压缩失败: {e}")
            return cv_image
    
    def upload_image(self, image_msg, name, reuse_threshold=600):  # 默认10分钟
        """
        上传图像到云端，如果指定时间内已上传过则复用之前的URL
        
        Args:
            image_msg: sensor_msgs/Image格式的图像消息
            name: 人脸名称，用于去重
            reuse_threshold: 重复使用URL的时间阈值（秒），默认600秒（10分钟）
        
        Returns:
            str: 图像URL，如果上传失败则返回None
        """
        current_time = time.time()
        
        # 检查是否在去重时间内
        with self.record_lock:
            if name in self.upload_records:
                last_upload_time, last_url = self.upload_records[name]
                if current_time - last_upload_time < reuse_threshold:
                    self.logger.info(f"图像上传去重：{name} 在 {reuse_threshold} 秒内，复用上次URL")
                    return last_url
        
        # 执行上传
        try:
            # 将图像消息转换为OpenCV格式
            bridge = CvBridge()
            cv_image = bridge.imgmsg_to_cv2(image_msg, "bgr8")
            
            # 压缩图像
            cv_image = self._compress_image(cv_image)
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                success, encoded_image = cv2.imencode(
                    '.jpg',
                    cv_image,
                    [cv2.IMWRITE_JPEG_QUALITY, self.image_quality]
                )

                if not success:
                    self.logger.error("图像编码失败")
                    return None

                encoded_image.tobytes()  # 获取字节数据
                tmp_file.write(encoded_image.tobytes())
                temp_image_path = tmp_file.name

            try:
                # 获取Token
                token = self._get_lsky_token()
                if not token:
                    self.logger.error("[上传] 无法获取Token，上传失败")
                    return None

                # 上传到Lsky Pro图床（使用Token认证）
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }

                with open(temp_image_path, 'rb') as f:
                    files = {'file': f}
                    # Nathan账号需要强制指定strategy_id
                    data = {'strategy_id': self.lsky_strategy_id} if self.lsky_strategy_id else {}

                    response = requests.post(
                        f"{self.lsky_base_url}/upload",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=60
                    )

                result = response.json()

                if result.get("status") and result.get("data", {}).get("links", {}).get("url"):
                    image_url = result["data"]["links"]["url"]
                    self.logger.info(f"[上传] 图片上传成功: {image_url}")
                    
                    # 更新记录
                    with self.record_lock:
                        self.upload_records[name] = (current_time, image_url)
                    
                    return image_url
                else:
                    message = result.get("message", "未知错误")
                    self.logger.error(f"[上传] 图片上传失败: {message}")
                    return None

            except Exception as e:
                self.logger.error(f"[上传] 上传异常: {e}")
                import traceback
                self.logger.error(f"[上传] 详细错误: {traceback.format_exc()}")
                return None

            finally:
                # 清理临时文件
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)

        except Exception as e:
            self.logger.error(f"[上传] 处理图像时出错: {e}")
            import traceback
            self.logger.error(f"[上传] 详细错误: {traceback.format_exc()}")
            return None


# 全局图像上传器实例
_global_image_uploader = None
_uploader_lock = threading.RLock()  # 使用可重入锁确保线程安全


def get_image_uploader():
    """
    获取全局图像上传器实例

    Returns:
        ImageUploader: 图像上传器实例
    """
    global _global_image_uploader
    if _global_image_uploader is None:
        with _uploader_lock:
            if _global_image_uploader is None:  # double-check locking
                _global_image_uploader = ImageUploader()
    return _global_image_uploader