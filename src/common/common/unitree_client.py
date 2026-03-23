"""
Unitree机器人客户端
通过socket与Unitree控制服务器通信
"""
import socket
import json
import struct
import threading
import traceback

# 导入日志配置
from .logger_config import get_logger

# 创建日志记录器
logger = get_logger(__name__)


class UnitreeClient:
    def __init__(self, server_host="127.0.0.1", server_port=9090):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self._lock = threading.Lock()
        
        # 连接到Unitree控制服务器
        self._connect()
    
    def _connect(self):
        """连接到Unitree控制服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            logger.info(f"✅ Connected to Unitree Control Server at {self.server_host}:{self.server_port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Unitree Control Server: {e}")
            raise
    
    def _send_command(self, command_data):
        """发送命令到服务器并接收响应"""
        with self._lock:
            try:
                # 序列化命令
                cmd_json = json.dumps(command_data)
                cmd_bytes = cmd_json.encode('utf-8')
                cmd_length = len(cmd_bytes)
                
                # 发送命令长度
                self.socket.sendall(struct.pack('!I', cmd_length))
                # 发送命令数据
                self.socket.sendall(cmd_bytes)
                
                # 接收响应长度
                response_length_data = self.socket.recv(4)
                if not response_length_data:
                    raise Exception("No response from server")
                
                response_length = struct.unpack('!I', response_length_data)[0]
                
                # 接收响应数据
                response_data = self.socket.recv(response_length)
                if not response_data:
                    raise Exception("No response data from server")
                
                response_json = response_data.decode('utf-8')
                response = json.loads(response_json)
                
                return response
                
            except Exception as e:
                logger.error(f"❌ Error communicating with Unitree Control Server: {e}")
                logger.error(traceback.format_exc())
                # 尝试重连
                try:
                    self.socket.close()
                except:
                    pass
                self._connect()
                raise e

    def shake_hand(self):
        """执行握手动作"""
        try:
            response = self._send_command({"action": "shake_hand"})
            return response
        except Exception as e:
            raise e
    
    def high_stand(self):
        """站立动作"""
        try:
            response = self._send_command({"action": "high_stand"})
            return response
        except Exception as e:
            raise e
    
    def sit(self):
        """坐下动作"""
        try:
            response = self._send_command({"action": "sit"})
            return response
        except Exception as e:
            raise e
    
    def stop_move(self):
        """停止移动"""
        try:
            response = self._send_command({"action": "stop_move"})
            return response
        except Exception as e:
            raise e
    
    def move(self, vx=0.0, vy=0.0, theta=0.0):
        """移动"""
        try:
            response = self._send_command({
                "action": "move",
                "vx": vx,
                "vy": vy,
                "theta": theta
            })
            return response
        except Exception as e:
            raise e
    
    def speak(self, text, volume=80):
        """说话"""
        try:
            response = self._send_command({
                "action": "speak",
                "text": text,
                "volume": volume
            })
            return response
        except Exception as e:
            raise e
    
    def led_control(self, r=0, g=0, b=0):
        """LED控制"""
        try:
            response = self._send_command({
                "action": "led_control",
                "r": r,
                "g": g,
                "b": b
            })
            return response
        except Exception as e:
            raise e
    
    def destroy(self):
        """清理资源"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass