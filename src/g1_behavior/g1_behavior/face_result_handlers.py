"""
人脸识别结果处理器模块
定义了处理人脸识别结果的接口和具体实现，支持多种行为响应（如打招呼、企业微信通知等）

注意：使用企业微信功能需要安装websocket-client库：
pip install websocket-client

企业微信机器人配置（Bot ID、Secret等）在WeChatWorkApiRequestHandler类的__init__方法中定义

重要提醒：企业微信机器人必须先由目标用户主动发起对话，之后机器人才能主动发送消息给该用户！
"""

from abc import ABC, abstractmethod
from g1_interfaces.msg import FaceResult
import threading
from typing import Dict
import rclpy
from rclpy.node import Node

from threading import Thread, Lock

from common.unitree_client import UnitreeClient

# 企业微信相关导入
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("Warning: websocket-client not installed. Install with: pip install websocket-client")

import json
import time
import uuid
import ssl
from datetime import datetime, timezone
import pytz
from cv_bridge import CvBridge
import cv2


class FaceResultHandler(ABC):
    """
    人脸识别结果处理器抽象基类
    """
    
    @abstractmethod
    def handle(self, face_result: FaceResult) -> bool:
        """
        处理人脸识别结果
        
        Args:
            face_result: 人脸识别结果消息
            
        Returns:
            bool: 处理是否成功
        """
        pass


class FaceResultProcessor:
    """
    人脸识别结果处理器管理器
    负责注册和分发人脸识别结果到不同的处理器
    """

    def __init__(self):
        self.handlers: Dict[str, FaceResultHandler] = {}
        self.lock = threading.Lock()  # 线程安全锁

    def register_handler(self, name: str, handler: FaceResultHandler):
        """
        注册处理器

        Args:
            name: 处理器名称
            handler: 处理器实例
        """
        with self.lock:
            self.handlers[name] = handler

    def unregister_handler(self, name: str):
        """
        注销处理器

        Args:
            name: 处理器名称
        """
        with self.lock:
            if name in self.handlers:
                del self.handlers[name]

    def get_handler(self, name: str):
        """
        获取指定名称的处理器

        Args:
            name: 处理器名称

        Returns:
            处理器实例或None
        """
        with self.lock:
            return self.handlers.get(name)

    def process(self, face_result: FaceResult):
        """
        处理人脸识别结果

        Args:
            face_result: 人脸识别结果消息
        """
        print(f"[DEBUG] FaceResultProcessor.process() called with name: {face_result.name}, similarity: {face_result.similarity}")
        with self.lock:
            print(f"[DEBUG] Number of handlers: {len(self.handlers)}")
            for name, handler in self.handlers.items():
                print(f"[DEBUG] Processing with handler: {name}")
                try:
                    success = handler.handle(face_result)
                    if not success:
                        print(f"Handler {name} failed to process face result")
                    else:
                        print(f"Handler {name} processed face result successfully")
                except Exception as e:
                    print(f"Error in handler {name}: {e}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")


class GreetingHandler(FaceResultHandler):
    """
    打招呼处理器
    当检测到已知面孔时触发问候行为（语音和动作）
    """

    def __init__(self, node: Node):
        self.node = node
        
        # 初始化UnitreeClient用于直接控制机器人
        try:
            self.unitree_client = UnitreeClient()
            self.node.get_logger().info("UnitreeClient initialized for direct robot control")
        except Exception as e:
            self.node.get_logger().error(f"Failed to initialize UnitreeClient: {e}")
            raise

        # 人脸去重记录 {name: timestamp}
        self.last_seen = {}
        # 当前机器人状态
        self.robot_state = "IDLE"
        # 去重时间阈值（秒）
        self.dedup_interval = 15.0

        # 添加锁来保护共享资源
        self.state_lock = Lock()  # 保护self.robot_state变量避免多个地方修改
        self.seen_lock = Lock()  # 保护人脸字典多个地方修改

    def handle(self, face_result: FaceResult) -> bool:
        """
        处理人脸识别结果，如果相似度足够高则触发问候

        Args:
            face_result: 人脸识别结果消息

        Returns:
            bool: 处理是否成功
        """
        self.node.get_logger().info(f"[DEBUG] Received face result - Name: {face_result.name}, Similarity: {face_result.similarity}")
        
        # 获取当前机器人状态
        with self.state_lock:
            current_state = self.robot_state

        self.node.get_logger().info(f"[DEBUG] Current robot state: {current_state}")
        
        # 如果正在打招呼 忽略
        if current_state == "GREETING":
            self.node.get_logger().info(
                f"Robot greeting, ignore!"
            )
            return True

        name = face_result.name
        similarity = face_result.similarity
        self.node.get_logger().info(f"[DEBUG] Processing face recognition - Name: {name}, Similarity: {similarity}")
        
        # 相似度过滤
        if similarity < 0.6:
            self.node.get_logger().info(f"[DEBUG] Face similarity {similarity} is below threshold, ignoring")
            return True

        # 使用 ROS2 时钟进行去重检查
        now = self.node.get_clock().now().nanoseconds / 1e9
        self.node.get_logger().info(f"[DEBUG] Checking deduplication for {name}")
        with self.seen_lock:
            if name in self.last_seen:
                time_since_last = now - self.last_seen[name]
                self.node.get_logger().info(f"[DEBUG] Last seen {name} {time_since_last}s ago, threshold is {self.dedup_interval}s")
                if time_since_last < self.dedup_interval:
                    self.node.get_logger().info(f"[DEBUG] Deduplication active, ignoring face recognition for {name}")
                    return True
            self.last_seen[name] = now

        self.node.get_logger().info(
            f"Face detected: {name}, triggering greeting sequence"
        )
        # 使用线程 避免阻塞 ROS 回调导致 rclpy.spin 无法处理其他消息
        self.node.get_logger().info(f"[DEBUG] Starting greeting thread for {name}")
        Thread(target=self._handle_greeting, args=(name,), daemon=True).start()

        return True
    
    def _handle_greeting(self, name: str):
        """
        内部方法：执行具体的问候逻辑

        Args:
            name: 检测到的人名
        """
        self.node.get_logger().info(f"[DEBUG] Starting greeting sequence for {name}")

        # 执行打招呼
        with self.state_lock:
            self.robot_state = "GREETING"
            self.node.get_logger().info(f"[DEBUG] Robot state set to GREETING")

        # 创建线程同时执行语音和动作
        import threading

        def play_audio():
            self.node.get_logger().info(f"[DEBUG] Starting audio thread for {name}")
            self._say_hello(name)
            self.node.get_logger().info(f"[DEBUG] Audio thread for {name} completed")

        def play_motion():
            self.node.get_logger().info(f"[DEBUG] Starting motion thread for {name}")
            try:
                # 直接执行挥手动作
                self.node.get_logger().info(f"Executing wave_hand action for {name}")
                self.unitree_client.shake_hand()
                # 等待动作完成
                import time
                time.sleep(10.0)  # 等待握手动作完成
                # 回到站立状态
                self.unitree_client.high_stand()
                self.node.get_logger().info(f"[DEBUG] Wave hand action completed successfully for {name}")
            except Exception as e:
                self.node.get_logger().error(f"Failed to execute motion command: {e}")
                import traceback
                self.node.get_logger().error(f"Motion command error details: {traceback.format_exc()}")

        # 并发执行语音和动作
        audio_thread = threading.Thread(target=play_audio)
        motion_thread = threading.Thread(target=play_motion)

        self.node.get_logger().info(f"[DEBUG] Starting audio and motion threads for {name}")
        audio_thread.start()
        motion_thread.start()

        # 等待两个线程完成
        self.node.get_logger().info(f"[DEBUG] Waiting for audio and motion threads to complete for {name}")
        audio_thread.join()
        motion_thread.join()
        self.node.get_logger().info(f"[DEBUG] Audio and motion threads completed for {name}")

        with self.state_lock:
            self.robot_state = "IDLE"
            self.node.get_logger().info(f"[DEBUG] Robot state reset to IDLE")

        self.node.get_logger().info(
            f"Greeting finished: {name}"
        )

    def _say_hello(self, name: str):
        """
        内部方法：播放问候语音

        Args:
            name: 检测到的人名
        """
        self.node.get_logger().info(f"[DEBUG] Starting audio greeting for {name}")

        # 播放英文语音问候
        if self.unitree_client:
            self.node.get_logger().info(f"[DEBUG] Unitree client is available, proceeding with TTS")
            try:
                greeting_text = f"Nice to meet you {name}!"
                self.node.get_logger().info(f"Playing greeting: {greeting_text}")

                self.node.get_logger().info(f"[DEBUG] Setting LED to green")
                # 使用UnitreeClient控制LED
                self.unitree_client.led_control(0, 255, 0)  # 设置LED为绿色

                self.node.get_logger().info(f"[DEBUG] Calling TTS Maker with text: {greeting_text}")
                # 使用UnitreeClient播放TTS
                result = self.unitree_client.speak(greeting_text, 80)  # 播放英文问候语，音量80%

                # 检查TTS是否成功
                if result and result.get("status") == "success":
                    self.node.get_logger().info("TTS playback initiated successfully")
                else:
                    self.node.get_logger().warning("TTS playback initiation failed")

                # 等待语音播放完成，固定等待5秒
                import time
                estimated_duration = 5.0  # 固定等待5秒
                self.node.get_logger().info(f"[DEBUG] Fixed audio duration: {estimated_duration}s, sleeping...")
                time.sleep(estimated_duration)
                self.node.get_logger().info(f"[DEBUG] Audio playback sleep completed")
            except Exception as e:
                self.node.get_logger().error(f"Failed to play audio greeting: {e}")
                import traceback
                self.node.get_logger().error(f"Detailed error: {traceback.format_exc()}")
            finally:
                # 确保LED最终被关闭
                try:
                    self.node.get_logger().info(f"[DEBUG] Turning off LED")
                    # 使用UnitreeClient关闭LED
                    self.unitree_client.led_control(0, 0, 0)  # 关闭LED
                    self.node.get_logger().info(f"[DEBUG] LED turned off successfully")
                except Exception as e:
                    self.node.get_logger().error(f"Failed to turn off LED: {e}")
        else:
            self.node.get_logger().warning("Unitree client not available, skipping audio greeting")
            # 添加额外的日志以便调试
            self.node.get_logger().info(f"Unitree client status: {self.unitree_client}")

        # 同时输出日志
        text = f"Hello {name}"
        self.node.get_logger().info(text)

        self.node.get_logger().info(f"[DEBUG] Audio greeting for {name} completed")


class WeChatWorkApiRequestHandler(FaceResultHandler):
    """
    企业微信API请求处理器
    当检测到人脸时通过企业微信发送识别消息（先上传图片到云端，再发送URL）
    """

    def __init__(self, node: Node):
        self.node = node

        # 企业微信机器人配置
        self.bot_id = "aibPK7lIHLBWw8DTawBKdyh1Q9cwXIqp29I"  # 请替换为实际的Bot ID
        self.secret = "DraM3GAPGWuGCeX50pDkasYXtnFiPsaIrjyNAh82xn7"  # 请替换为实际的Secret
        self.target_user = "LiHuo"  # 请替换为实际的目标用户ID
        self.ws_url = "wss://openws.work.weixin.qq.com"

        # Lsky Pro 图床配置
        self.lsky_base_url = "http://tiagent.tech:7791/api/v1"  # 使用域名
        self.lsky_email = "Nathan@Haitch.cn"  # Nathan账号
        self.lsky_password = "12345678"  # Nathan密码
        self.lsky_strategy_id = 1  # 强制使用策略ID 1

        # 图片压缩参数
        self.image_quality = 30  # 图片压缩质量（1-100）
        self.max_image_size = 480  # 图片最大边长（像素）

        # 人脸识别去重机制 - 记录每个人脸最后发送时间
        self.duplicate_interval = 180  # 3分钟（秒）

        # 检查必要的库是否可用
        self.websocket_available = WEBSOCKET_AVAILABLE
        try:
            import requests
            self.requests_available = True
        except ImportError:
            self.requests_available = False
            self.node.get_logger().error("requests库未安装，请运行: pip install requests")

        if not self.websocket_available:
            self.node.get_logger().error("websocket库未安装，请运行: pip install websocket-client")

        # WebSocket连接相关
        self.ws_app = None
        self.is_connected = False
        self.is_authenticated = False

        # 用于存储发送消息的队列
        self.message_queue = []
        self.queue_lock = threading.Lock()

        # 心跳线程
        self.heartbeat_thread = None
        self.heartbeat_stop_event = threading.Event()

        # 人脸识别去重机制 - 记录每个人脸最后发送时间
        self.face_last_sent = {}

        # 缓存最新图像
        self.latest_image = None
        self.image_lock = threading.Lock()

        # 重要提醒
        self.node.get_logger().warn("重要提醒：企业微信机器人必须先由目标用户主动发起对话，之后机器人才能主动发送消息给该用户！")
        self.node.get_logger().info(f"配置的机器人ID: {self.bot_id}, 目标用户: {self.target_user}")

        # 尝试初始化连接
        if self.websocket_available:
            self._initialize_connection()
    
    def update_latest_image(self, image_msg):
        """
        更新最新图像缓存
        
        Args:
            image_msg: sensor_msgs/Image 消息
        """
        with self.image_lock:
            self.latest_image = image_msg

    def _initialize_connection(self):
        """初始化WebSocket连接"""
        try:
            self.ws_app = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # 在后台线程启动WebSocket连接
            import threading
            ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            ws_thread.start()
            
            # 等待连接建立
            timeout = 10  # 10秒超时
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                self.node.get_logger().info("企业微信WebSocket连接初始化成功")
            else:
                self.node.get_logger().error("企业微信WebSocket连接初始化超时")
                
        except Exception as e:
            self.node.get_logger().error(f"初始化WebSocket连接时出错: {e}")
    
    def _run_websocket(self):
        """运行WebSocket连接"""
        self.ws_app.run_forever(
            sslopt={"cert_reqs": ssl.CERT_NONE},
            ping_interval=25,  # 每25秒发送一次ping，与原代码一致
            ping_timeout=10    # ping超时时间10秒
        )
    
    def _start_heartbeat(self):
        """启动心跳机制"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return  # 心跳线程已经在运行
        
        self.heartbeat_stop_event.clear()
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
    
    def _heartbeat_worker(self):
        """心跳工作线程"""
        while not self.heartbeat_stop_event.is_set():
            try:
                time.sleep(30)  # 每30秒发送一次心跳
                if self.is_connected and self.ws_app and self.ws_app.sock and self.ws_app.sock.connected:
                    req_id = str(uuid.uuid4())
                    ping_msg = {
                        "cmd": "ping",
                        "headers": {
                            "req_id": req_id
                        }
                    }
                    self.ws_app.send(json.dumps(ping_msg))
                    self.node.get_logger().info(f"[INFO] 心跳发送 (req_id: {req_id})")
                else:
                    self.node.get_logger().info("[INFO] WebSocket未连接，跳过心跳")
            except Exception as e:
                self.node.get_logger().error(f"[ERROR] 发送心跳失败: {e}")
                break
    
    def _on_open(self, ws):
        """连接打开时的回调"""
        self.node.get_logger().info("[OK] WebSocket 连接已建立")
        # 线程安全地更新连接状态
        with self.queue_lock:
            self.is_connected = True
            self.is_authenticated = False  # 连接刚建立时还未认证
        
        # 发送认证请求
        self._send_subscribe(ws)
    
    def _on_message(self, ws, message):
        """收到消息时的回调"""
        try:
            self.node.get_logger().info(f"[RECV] 原始消息: {message[:200]}...")  # 只显示前200个字符避免日志过长
            data = json.loads(message)
            self.node.get_logger().info(f"[RECV] 解析后CMD: {data.get('cmd', 'unknown')}")

            cmd = data.get("cmd", "")
            errcode = data.get("errcode", 0)
            errmsg = data.get("errmsg", "")
            headers = data.get("headers", {})
            req_id = headers.get("req_id", "")

            # 认证响应处理：如果存在req_id但cmd为空或不是已知命令，则认为是认证相关响应
            if req_id and (not cmd or cmd in ["", "unknown"]):
                if errcode == 0:
                    # 认证成功
                    self.node.get_logger().info("[OK] 认证成功！机器人已就绪")
                    # 确保状态更新是线程安全的
                    with self.queue_lock:  # 使用现有的锁来保证线程安全
                        self.is_authenticated = True
                    # 启动心跳机制
                    self._start_heartbeat()
                    self.node.get_logger().info("心跳机制已启动")
                    self.node.get_logger().info("认证完成，现在可以发送消息（前提是用户已与机器人对话）")
                else:
                    # 认证失败
                    self.node.get_logger().error(f"[ERROR] 认证失败: {errmsg} (errcode: {errcode})")
                    # 确保状态更新是线程安全的
                    with self.queue_lock:  # 使用现有的锁来保证线程安全
                        self.is_authenticated = False
            # 发送消息响应
            elif cmd == "aibot_send_msg_resp":
                req_id = data.get("headers", {}).get("req_id", "unknown")
                msg_type = data.get("body", {}).get("msgtype", "unknown") if "body" in data else "unknown"
                if errcode == 0:
                    self.node.get_logger().info(f"[OK] 消息发送成功 (req_id: {req_id}, type: {msg_type})")
                else:
                    self.node.get_logger().error(f"[ERROR] 消息发送失败 {errmsg} (req_id: {req_id}, errcode: {errcode}, type: {msg_type})")

            # 收到用户消息（被动接收）
            elif cmd == "aibot_msg_callback":
                body = data.get("body", {})
                from_user = body.get("from", {}).get("userid", "未知用户")
                msg_type = body.get("msgtype", "text")

                if msg_type == "text":
                    text_content = body.get("text", {}).get("content", "")
                    self.node.get_logger().info(f"[CHAT] 收到 {from_user} 的消息: {text_content}")
                else:
                    self.node.get_logger().info(f"[CHAT] 收到 {from_user} 的{msg_type}类型消息")

            # 收到事件回调
            elif cmd == "aibot_event_callback":
                body = data.get("body", {})
                event_info = body.get("event", {})
                event_type = event_info.get("eventtype", "unknown")
                self.node.get_logger().info(f"[EVENT] 收到事件: {event_type}")

        except json.JSONDecodeError:
            self.node.get_logger().info(f"[RECV] 非JSON消息: {message[:100]}...")
        except Exception as e:
            self.node.get_logger().error(f"[ERROR] 处理消息时出错: {e}")
            import traceback
            self.node.get_logger().error(f"[ERROR] 详细错误堆栈: {traceback.format_exc()}")
    
    def _on_error(self, ws, error):
        """发生错误时的回调"""
        self.node.get_logger().error(f"[ERROR] WebSocket 错误: {error}")
        # 线程安全地更新状态
        with self.queue_lock:
            self.is_connected = False
            self.is_authenticated = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭时的回调"""
        self.node.get_logger().info(f"[INFO] WebSocket 连接已关闭")
        if close_status_code:
            self.node.get_logger().info(f"       状态码: {close_status_code}")
        if close_msg:
            self.node.get_logger().info(f"       原因: {close_msg}")
        
        # 停止心跳
        self.heartbeat_stop_event.set()
        
        # 线程安全地更新状态
        with self.queue_lock:
            self.is_connected = False
            self.is_authenticated = False
        
        # 尝试重连
        self.node.get_logger().info("尝试重新连接...")
        time.sleep(5)  # 等待5秒后重连
        self._initialize_connection()
    
    def _send_subscribe(self, ws):
        """发送认证请求"""
        req_id = str(uuid.uuid4())
        subscribe_msg = {
            "cmd": "aibot_subscribe",
            "headers": {
                "req_id": req_id
            },
            "body": {
                "bot_id": self.bot_id,
                "secret": self.secret
            }
        }
        message = json.dumps(subscribe_msg, ensure_ascii=False)
        self.node.get_logger().info(f"[SEND] 认证请求: {message}")
        ws.send(message)
        self.node.get_logger().info(f"[INFO] 已发送认证请求（req_id: {req_id}）")
        
    def handle(self, face_result: FaceResult) -> bool:
        """
        处理人脸识别结果，通过企业微信发送识别消息

        Args:
            face_result: 人脸识别结果消息

        Returns:
            bool: 处理是否成功
        """
        if not self.websocket_available:
            self.node.get_logger().error("WebSocket库不可用，无法发送企业微信消息")
            return False

        # 线程安全地检查认证状态
        with self.queue_lock:
            is_authenticated = self.is_authenticated
            is_connected = self.is_connected

        if not is_connected:
            self.node.get_logger().error("WebSocket未连接，无法发送消息")
            return False

        if not is_authenticated:
            self.node.get_logger().error("企业微信未认证，无法发送消息")
            # 检查是否正在认证过程中
            self.node.get_logger().info(f"当前连接状态: {is_connected}, 认证状态: {is_authenticated}")
            return False

        # 检查是否在去重时间内
        current_time = self.node.get_clock().now().nanoseconds / 1e9
        person_key = face_result.name

        with self.queue_lock:  # 使用锁保护共享状态
            if person_key in self.face_last_sent:
                last_sent_time = self.face_last_sent[person_key]
                if current_time - last_sent_time < self.duplicate_interval:
                    # 在去重时间内，不发送消息
                    elapsed = current_time - last_sent_time
                    remaining = self.duplicate_interval - elapsed
                    self.node.get_logger().info(f"人脸识别去重：{person_key} 在 {remaining:.0f} 秒内，跳过发送")
                    return True  # 返回True表示处理成功（只是跳过了发送）

            # 更新最后发送时间
            self.face_last_sent[person_key] = current_time

        try:
            # 将时间转换为北京时间
            beijing_tz = pytz.timezone('Asia/Shanghai')
            current_time_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
            beijing_time = current_time_dt.astimezone(beijing_tz)
            formatted_time = beijing_time.strftime('%Y-%m-%d %H:%M:%S')

            # 构建要发送的消息内容
            message_content = f"人脸识别通知：\n\n**姓名**：{face_result.name}\n**相似度**：{face_result.similarity:.2f}\n**时间**：{formatted_time}"

            self.node.get_logger().info(f"准备发送人脸识别信息到企业微信: {message_content}")

            # 发送企业微信消息（包含文本和图片）
            success = self._send_wechat_work_message(message_content)

            if success:
                self.node.get_logger().info("企业微信消息（含图片）发送成功")
            else:
                self.node.get_logger().error("企业微信消息发送失败")

            return success

        except Exception as e:
            self.node.get_logger().error(f"处理企业微信API请求时发生错误: {e}")
            import traceback
            self.node.get_logger().error(f"错误详情: {traceback.format_exc()}")
            return False

    def _get_lsky_token(self):
        """
        通过Nathan账号获取Lsky Pro的Token
        """
        if not self.requests_available:
            self.node.get_logger().error("requests库不可用，无法获取Token")
            return None

        try:
            import requests

            url = f"{self.lsky_base_url}/tokens"
            data = {
                "email": self.lsky_email,
                "password": self.lsky_password
            }
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            self.node.get_logger().info(f"[上传] 正在使用Nathan账号登录获取Token...")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            result = response.json()

            if result.get("status") and result.get("data", {}).get("token"):
                token = result["data"]["token"]
                self.node.get_logger().info(f"[上传] 登录成功! Token: {token[:20]}...")
                return token
            else:
                message = result.get("message", "未知错误")
                self.node.get_logger().error(f"[上传] 登录失败: {message}")
                return None

        except Exception as e:
            self.node.get_logger().error(f"[上传] 获取Token异常: {e}")
            import traceback
            self.node.get_logger().error(f"[上传] 详细错误: {traceback.format_exc()}")
            return None

    def _upload_image_to_cloud(self, image_msg):
        """
        使用Nathan账号上传图像到云端图床并返回URL
        """
        if not self.requests_available:
            self.node.get_logger().error("requests库不可用，无法上传图片到云端")
            return None

        try:
            import requests
            import tempfile
            import os

            # 获取Token
            token = self._get_lsky_token()
            if not token:
                self.node.get_logger().error("[上传] 无法获取Token，上传失败")
                return None

            # 将图像消息转换为OpenCV格式
            bridge = CvBridge()
            cv_image = bridge.imgmsg_to_cv2(image_msg, "bgr8")

            # 压缩图像
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

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                success, encoded_image = cv2.imencode(
                    '.jpg',
                    cv_image,
                    [cv2.IMWRITE_JPEG_QUALITY, self.image_quality]
                )

                if not success:
                    self.node.get_logger().error("图像编码失败")
                    return None

                encoded_image.tobytes()  # 获取字节数据
                tmp_file.write(encoded_image.tobytes())
                temp_image_path = tmp_file.name

            try:
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
                    self.node.get_logger().info(f"[上传] 图片上传成功: {image_url}")
                    return image_url
                else:
                    message = result.get("message", "未知错误")
                    self.node.get_logger().error(f"[上传] 图片上传失败: {message}")
                    return None

            except Exception as e:
                self.node.get_logger().error(f"[上传] 上传异常: {e}")
                import traceback
                self.node.get_logger().error(f"[上传] 详细错误: {traceback.format_exc()}")
                return None

            finally:
                # 清理临时文件
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)

        except Exception as e:
            self.node.get_logger().error(f"[上传] 处理图像时出错: {e}")
            import traceback
            self.node.get_logger().error(f"[上传] 详细错误: {traceback.format_exc()}")
            return None

    def _send_wechat_work_message_with_url(self, content: str, image_url: str = None) -> bool:
        """
        通过企业微信发送消息（使用URL形式的图片）
        """
        with self.queue_lock:
            if not self.is_connected or not self.is_authenticated:
                self.node.get_logger().error("WebSocket未连接或未认证")
                return False

        try:
            # 构建包含图片URL的Markdown内容
            if image_url:
                full_content = f"{content}\n\n![人脸识别图片]({image_url})"
            else:
                full_content = content

            # 发送Markdown消息（包含图片URL）
            req_id = str(uuid.uuid4())
            msg = {
                "cmd": "aibot_send_msg",
                "headers": {"req_id": req_id},
                "body": {
                    "chatid": self.target_user,
                    "chat_type": 1,
                    "msgtype": "markdown",
                    "markdown": {"content": full_content}
                }
            }

            self.ws_app.send(json.dumps(msg, ensure_ascii=False))
            self.node.get_logger().info(f"[发送] Markdown消息 (req_id: {req_id})")
            if image_url:
                self.node.get_logger().info(f"[发送] 图片URL: {image_url}")

            return True

        except Exception as e:
            self.node.get_logger().error(f"发送企业微信消息出错: {e}")
            import traceback
            self.node.get_logger().error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def _send_wechat_work_message(self, content: str) -> bool:
        """
        发送企业微信消息（先上传图片到云端，再发送包含URL的消息）
        """
        with self.queue_lock:
            if not self.is_connected or not self.is_authenticated:
                self.node.get_logger().error("WebSocket未连接或未认证")
                return False

        try:
            # 异步上传图片并发送消息
            import threading
            upload_and_send_thread = threading.Thread(
                target=self._upload_and_send_in_thread,
                args=(content,),
                daemon=True
            )
            upload_and_send_thread.start()

            return True  # 操作启动成功

        except Exception as e:
            self.node.get_logger().error(f"启动上传和发送线程出错: {e}")
            import traceback
            self.node.get_logger().error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def _upload_and_send_in_thread(self, content: str):
        """
        在独立线程中上传图片并发送消息
        """
        try:
            # 上传图片到云端
            image_url = None
            with self.image_lock:
                if self.latest_image:
                    image_url = self._upload_image_to_cloud(self.latest_image)

            # 发送消息（包含图片URL）
            success = self._send_wechat_work_message_with_url(content, image_url)
            
            if success:
                self.node.get_logger().info("企业微信消息（含云端图片URL）发送成功")
            else:
                self.node.get_logger().error("企业微信消息发送失败")

        except Exception as e:
            self.node.get_logger().error(f"上传和发送过程中出错: {e}")
            import traceback
            self.node.get_logger().error(f"详细错误信息: {traceback.format_exc()}")
    
    
