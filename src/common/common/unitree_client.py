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

        self._connect()

    def _connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            logger.info(f"✅ Connected to Unitree Control Server")
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            raise

    def _send_command(self, data):
        with self._lock:
            try:
                payload = json.dumps(data).encode()
                self.socket.sendall(struct.pack('!I', len(payload)))
                self.socket.sendall(payload)

                length = struct.unpack('!I', self.socket.recv(4))[0]
                resp = self.socket.recv(length)

                return json.loads(resp.decode())

            except Exception as e:
                logger.error(f"❌ Communication error: {e}")
                self._reconnect()
                raise

    def _reconnect(self):
        try:
            self.socket.close()
        except:
            pass
        self._connect()

    # =========================
    # ⭐ 行为接口（核心）
    # =========================

    def do_behavior(self, name, **params):
        return self._send_command({
            "type": "behavior",
            "name": name,
            "params": params
        })

    # =========================
    # ⭐ 控制接口（连续控制）
    # =========================

    def set_velocity(self, vx=0.0, vy=0.0, theta=0.0):
        return self._send_command({
            "type": "control",
            "name": "velocity",
            "vx": vx,
            "vy": vy,
            "theta": theta
        })

    def stop(self):
        return self.set_velocity(0, 0, 0)

    # =========================
    # ⭐ 系统接口
    # =========================

    def speak(self, text):
        return self._send_command({
            "type": "speech",
            "text": text
        })

    def set_led(self, r, g, b):
        return self._send_command({
            "type": "led",
            "r": r,
            "g": g,
            "b": b
        })

    def destroy(self):
        try:
            self.socket.close()
        except:
            pass