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
import time

from threading import Thread, Lock

from common.unitree_client import UnitreeClient
from common.audio_handler import AudioHandler
# 导入日志配置
from common.logger_config import get_logger

# 企业微信相关导入
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger = get_logger(__name__)
    logger.warning("Warning: websocket-client not installed. Install with: pip install websocket-client")

import json
import uuid
import ssl
import pytz


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
        self.logger = get_logger(self.__class__.__name__)

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
        self.logger.debug(f"[DEBUG] FaceResultProcessor.process() called with name: {face_result.name}, similarity: {face_result.similarity}")
        with self.lock:
            self.logger.debug(f"[DEBUG] Number of handlers: {len(self.handlers)}")
            for name, handler in self.handlers.items():
                self.logger.debug(f"[DEBUG] Processing with handler: {name}")
                try:
                    success = handler.handle(face_result)
                    if not success:
                        self.logger.error(f"Handler {name} failed to process face result")
                    else:
                        self.logger.info(f"Handler {name} processed face result successfully")
                except Exception as e:
                    self.logger.error(f"Error in handler {name}: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")


class GreetingHandler(FaceResultHandler):
    """
    打招呼处理器
    当检测到已知面孔时触发问候行为（语音和动作）
    """

    def __init__(self, node: Node):
        self.node = node

        # 使用自定义日志记录器
        self.logger = get_logger(f"{self.node.get_name()}.{self.__class__.__name__}")

        # 初始化UnitreeClient用于直接控制机器人，但允许连接失败
        self.unitree_client = None
        try:
            self.unitree_client = UnitreeClient()
            self.logger.info("UnitreeClient initialized for direct robot control")
        except Exception as e:
            self.logger.error(f"Failed to initialize UnitreeClient: {e}")
            self.logger.warning("Unitree control service unavailable, but program will continue running. Actions will be skipped, but voice greeting will still work.")
            # 不抛出异常，让程序继续运行

        # 初始化音频处理器
        try:
            self.audio_handler = AudioHandler()
            if self.audio_handler:
                self.logger.info("AudioHandler initialized for speech output")
            else:
                self.logger.warning("Failed to initialize AudioHandler, using fallback TTS")
        except Exception as e:
            self.logger.error(f"Failed to initialize AudioHandler: {e}")
            self.audio_handler = None

        # 人脸去重记录 {name: timestamp}
        self.last_seen = {}
        # 当前机器人状态
        self.robot_state = "IDLE"
        # 去重时间阈值（秒）
        self.dedup_interval = 5.0

        # 添加锁来保护共享资源
        self.state_lock = Lock()  # 保护self.robot_state变量避免多个地方修改
        self.seen_lock = Lock()  # 保护人脸字典多个地方修改

    def handle(self, face_result: FaceResult) -> bool:
        """
        处理人脸识别结果，根据相似度和姓名触发不同的问候

        Args:
            face_result: 人脸识别结果消息

        Returns:
            bool: 处理是否成功
        """
        self.logger.info(f"[DEBUG] Received face result - Name: {face_result.name}, Similarity: {face_result.similarity}")

        # 获取当前机器人状态
        with self.state_lock:
            current_state = self.robot_state

        self.logger.info(f"[DEBUG] Current robot state: {current_state}")

        # 如果正在打招呼 忽略
        if current_state == "GREETING":
            self.logger.info(
                f"Robot greeting, ignore!"
            )
            return True

        name = face_result.name
        similarity = face_result.similarity
        self.logger.info(f"[DEBUG] Processing face recognition - Name: {name}, Similarity: {similarity}")

        # 根据人脸识别结果决定问候内容
        if name and name.strip():  # 如果有人脸且有名字
            if similarity >= 0.6:  # 相似度大于等于0.6，按现有逻辑打招呼
                greeting_text = f"Hello {name}!"
            else:  # 相似度小于0.6，询问模式
                greeting_text = f"Hi, are you {name}? You look quite different lately!"
        else:  # 如果没有人脸或名字为空，欢迎模式
            greeting_text = "Hello, welcome to Haitch!"

        # 使用 ROS2 时钟进行去重检查（仅针对有名字的情况，避免每次无人脸都触发欢迎）
        if name and name.strip():
            now = self.node.get_clock().now().nanoseconds / 1e9
            self.logger.info(f"[DEBUG] Checking deduplication for {name}")
            with self.seen_lock:
                if name in self.last_seen:
                    time_since_last = now - self.last_seen[name]
                    self.logger.info(f"[DEBUG] Last seen {name} {time_since_last}s ago, threshold is {self.dedup_interval}s")
                    if time_since_last < self.dedup_interval:
                        self.logger.info(f"[DEBUG] Deduplication active, ignoring face recognition for {name}")
                        return True
                self.last_seen[name] = now
        else:
            # 对于无名访问者，我们仍可以限制欢迎频率，但使用通用标识
            now = self.node.get_clock().now().nanoseconds / 1e9
            anonymous_key = "__anonymous__"  # 使用特殊键来追踪无名访问者
            self.logger.info(f"[DEBUG] Checking deduplication for anonymous visitor")
            with self.seen_lock:
                if anonymous_key in self.last_seen:
                    time_since_last = now - self.last_seen[anonymous_key]
                    self.logger.info(f"[DEBUG] Last seen anonymous visitor {time_since_last}s ago, threshold is {self.dedup_interval}s")
                    if time_since_last < 3:
                        self.logger.info(f"[DEBUG] Deduplication active, ignoring anonymous visitor")
                        return True
                self.last_seen[anonymous_key] = now

        self.logger.info(
            f"Face detected: {name}, similarity: {similarity}, triggering greeting: '{greeting_text}'"
        )
        # 使用线程 避免阻塞 ROS 回调导致 rclpy.spin 无法处理其他消息
        self.logger.info(f"[DEBUG] Starting greeting thread for {name} with greeting: {greeting_text}")

        # 启动问候线程（已移除线程数量检查）
        Thread(target=self._handle_greeting_with_text, args=(name, greeting_text), daemon=True).start()

        return True

    def _handle_greeting_with_text(self, name: str, greeting_text: str):
        self.logger.info(f"[DEBUG] Starting greeting sequence for {name} with text: {greeting_text}")

        with self.state_lock:
            self.robot_state = "GREETING"

        try:
            if self.unitree_client:
                try:
                    # 根据是否有名字决定行为参数
                    if name and name.strip():
                        self.unitree_client.do_behavior(
                            "greet",
                            person_name=name
                        )
                except Exception as client_error:
                    self.logger.error(f"UnitreeClient greeting failed: {client_error}")
                    self.logger.info("Voice greeting only (no action due to UnitreeClient failure)")
            else:
                self.logger.info("UnitreeClient not available, greeting with voice only")

            # 使用外接扬声器播放问候语
            if self.audio_handler:
                self.logger.info(f"Playing greeting via external speaker: {greeting_text}")
                success = self.audio_handler.play_with_external_speaker(greeting_text)
                if not success:
                    self.logger.warning("Failed to play via external speaker, falling back to robot's built-in speaker")
                else:
                    self.logger.info("play_with_external_speaker is error!")
            else:
                self.logger.info("audio_handler not available!")
        except Exception as e:
            self.logger.error(f"Greeting failed: {e}")

        finally:
            with self.state_lock:
                self.robot_state = "IDLE"

        self.logger.info(f"Greeting finished: {name} with text: {greeting_text}")


class WeChatWorkApiRequestHandler(FaceResultHandler):
    """
    企业微信API请求处理器
    当检测到人脸时通过企业微信发送识别消息（先上传图片到云端，再发送URL）
    """

    def __init__(self, node: Node):
        self.node = node

        # 企业微信机器人配置 - 直接在代码中定义
        self.bot_id = "aibPK7lIHLBWw8DTawBKdyh1Q9cwXIqp29I"  # 请替换为实际的Bot ID
        self.secret = "DraM3GAPGWuGCeX50pDkasYXtnFiPsaIrjyNAh82xn7"  # 请替换为实际的Secret
        # self.target_users = ["maik", "LiHuo", "Na"]  # 目标用户列表，支持多个用户
        self.target_users = ["ZhouYangYang", "LiHuo", "Nathan"]  # 目标用户列表，支持多个用户

        self.ws_url = "wss://openws.work.weixin.qq.com"

        # 人脸识别去重机制 - 记录每个人脸最后发送时间
        self.duplicate_interval = 300  # 5分钟

        # 检查必要的库是否可用
        self.websocket_available = WEBSOCKET_AVAILABLE
        self.logger = get_logger(f"{self.node.get_name()}.{self.__class__.__name__}")

        if not self.websocket_available:
            self.logger.error("websocket库未安装，请运行: pip install websocket-client")

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

        # 重要提醒
        self.logger.warn("重要提醒：企业微信机器人必须先由目标用户主动发起对话，之后机器人才能主动发送消息给该用户！")
        self.logger.info(f"配置的机器人ID: {self.bot_id}, 目标用户: {self.target_users}")

        # 尝试初始化连接
        if self.websocket_available:
            self._initialize_connection()
    

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
                self.logger.info("企业微信WebSocket连接初始化成功")
            else:
                self.logger.error("企业微信WebSocket连接初始化超时")
                
        except Exception as e:
            self.logger.error(f"初始化WebSocket连接时出错: {e}")
    
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
                    self.logger.info(f"[INFO] 心跳发送 (req_id: {req_id})")
                else:
                    self.logger.info("[INFO] WebSocket未连接，跳过心跳")
            except Exception as e:
                self.logger.error(f"[ERROR] 发送心跳失败: {e}")
                break
    
    def _on_open(self, ws):
        """连接打开时的回调"""
        self.logger.info("[OK] WebSocket 连接已建立")
        # 线程安全地更新连接状态
        with self.queue_lock:
            self.is_connected = True
            self.is_authenticated = False  # 连接刚建立时还未认证
        
        # 发送认证请求
        self._send_subscribe(ws)
    
    def _on_message(self, ws, message):
        """收到消息时的回调"""
        try:
            self.logger.info(f"[RECV] 原始消息: {message[:200]}...")  # 只显示前200个字符避免日志过长
            data = json.loads(message)
            self.logger.info(f"[RECV] 解析后data: {data}")

            cmd = data.get("cmd", "")
            errcode = data.get("errcode", 0)
            errmsg = data.get("errmsg", "")
            headers = data.get("headers", {})
            req_id = headers.get("req_id", "")

            # 认证响应处理：如果存在req_id但cmd为空或不是已知命令，则认为是认证相关响应
            if req_id and (not cmd or cmd in ["", "unknown"]):
                if errcode == 0:
                    # 认证成功
                    self.logger.info("[OK] 认证成功！机器人已就绪")
                    # 确保状态更新是线程安全的
                    with self.queue_lock:  # 使用现有的锁来保证线程安全
                        self.is_authenticated = True
                    # 启动心跳机制
                    self._start_heartbeat()
                    self.logger.info("心跳机制已启动")
                    self.logger.info("认证完成，现在可以发送消息（前提是用户已与机器人对话）")
                else:
                    # 认证失败
                    self.logger.error(f"[ERROR] 认证失败: {errmsg} (errcode: {errcode})")
                    # 确保状态更新是线程安全的
                    with self.queue_lock:  # 使用现有的锁来保证线程安全
                        self.is_authenticated = False
            # 发送消息响应
            elif cmd == "aibot_send_msg_resp":
                req_id = data.get("headers", {}).get("req_id", "unknown")
                msg_type = data.get("body", {}).get("msgtype", "unknown") if "body" in data else "unknown"
                if errcode == 0:
                    self.logger.info(f"[OK] 消息发送成功 (req_id: {req_id}, type: {msg_type})")
                else:
                    self.logger.error(f"[ERROR] 消息发送失败 {errmsg} (req_id: {req_id}, errcode: {errcode}, type: {msg_type})")

            # 收到用户消息（被动接收）
            elif cmd == "aibot_msg_callback":
                body = data.get("body", {})
                from_user = body.get("from", {}).get("userid", "未知用户")
                msg_type = body.get("msgtype", "text")

                if msg_type == "text":
                    text_content = body.get("text", {}).get("content", "")
                    self.logger.info(f"[CHAT] 收到 {from_user} 的消息: {text_content}")
                else:
                    self.logger.info(f"[CHAT] 收到 {from_user} 的{msg_type}类型消息")

            # 收到事件回调
            elif cmd == "aibot_event_callback":
                body = data.get("body", {})
                event_info = body.get("event", {})
                event_type = event_info.get("eventtype", "unknown")
                self.logger.info(f"[EVENT] 收到事件: {event_type}")

        except json.JSONDecodeError:
            self.logger.info(f"[RECV] 非JSON消息: {message[:100]}...")
        except Exception as e:
            self.logger.error(f"[ERROR] 处理消息时出错: {e}")
            import traceback
            self.logger.error(f"[ERROR] 详细错误堆栈: {traceback.format_exc()}")
    
    def _on_error(self, ws, error):
        """发生错误时的回调"""
        self.logger.error(f"[ERROR] WebSocket 错误: {error}")
        # 线程安全地更新状态
        with self.queue_lock:
            self.is_connected = False
            self.is_authenticated = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭时的回调"""
        self.logger.info(f"[INFO] WebSocket 连接已关闭")
        if close_status_code:
            self.logger.info(f"       状态码: {close_status_code}")
        if close_msg:
            self.logger.info(f"       原因: {close_msg}")
        
        # 停止心跳
        self.heartbeat_stop_event.set()
        
        # 线程安全地更新状态
        with self.queue_lock:
            self.is_connected = False
            self.is_authenticated = False
        
        # 尝试重连
        self.logger.info("尝试重新连接...")
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
        self.logger.info(f"[SEND] 认证请求: {message}")
        ws.send(message)
        self.logger.info(f"[INFO] 已发送认证请求（req_id: {req_id}）")
        
    def handle(self, face_result: FaceResult) -> bool:
        """
        处理人脸识别结果，通过企业微信发送识别消息

        Args:
            face_result: 人脸识别结果消息

        Returns:
            bool: 处理是否成功
        """
        if not self.websocket_available:
            self.logger.error("WebSocket库不可用，无法发送企业微信消息")
            return False

        # 线程安全地检查认证状态
        with self.queue_lock:
            is_authenticated = self.is_authenticated
            is_connected = self.is_connected

        if not is_connected:
            self.logger.error("WebSocket未连接，无法发送消息")
            return False

        if not is_authenticated:
            self.logger.error("企业微信未认证，无法发送消息")
            # 检查是否正在认证过程中
            self.logger.info(f"当前连接状态: {is_connected}, 认证状态: {is_authenticated}")
            return False

        if not face_result.name:  # 陌生人不发生信息
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
                    self.logger.info(f"人脸识别去重：{person_key} 在 {remaining:.0f} 秒内，跳过发送")
                    return True  # 返回True表示处理成功（只是跳过了发送）

            # 更新最后发送时间
            self.face_last_sent[person_key] = current_time

        try:
            # 构建要发送的消息内容
            message_content = f"Face Recognition Notification: \n\n**Name**：{face_result.name}\n**Similarity Score**：{face_result.similarity:.2f}"

            # 使用传入的图像URL，不再从缓存获取
            image_url = face_result.image_url if face_result.image_url else None
            self.logger.info(f"获取到人脸图片URL: {image_url}")
            
            # 发送企业微信消息（包含文本和图片URL）
            success = self._send_wechat_work_message_with_url(message_content, image_url)

            if success:
                self.logger.info("企业微信消息（含图片URL）发送成功")
            else:
                self.logger.error("企业微信消息发送失败")

            return success

        except Exception as e:
            self.logger.error(f"处理企业微信API请求时发生错误: {e}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            return False


    def _send_wechat_work_message_with_url(self, content: str, image_url: str = None) -> bool:
        """
        通过企业微信发送消息（使用已有的图片URL）
        """
        with self.queue_lock:
            if not self.is_connected or not self.is_authenticated:
                self.logger.error("WebSocket未连接或未认证")
                return False

        try:
            # 构建包含图片URL的Markdown内容
            if image_url:
                full_content = f"{content}\n\n![人脸识别图片]({image_url})"
            else:
                full_content = content

            # 向所有配置的目标用户发送消息
            success_count = 0
            for target_user in self.target_users:

                # 发送Markdown消息（包含图片URL）
                req_id = str(uuid.uuid4())
                msg = {
                    "cmd": "aibot_send_msg",
                    "headers": {"req_id": req_id},
                    "body": {
                        "chatid": target_user,
                        "chat_type": 1,
                        "msgtype": "markdown",
                        "markdown": {"content": full_content}
                    }
                }

                self.ws_app.send(json.dumps(msg, ensure_ascii=False))
                self.logger.info(f"[发送] Markdown消息给 {target_user} (req_id: {req_id})")
                if image_url:
                    self.logger.info(f"[发送] 图片URL: {image_url}")
                
                success_count += 1

            self.logger.info(f"成功向 {success_count} 个用户发送了消息")
            return success_count > 0

        except Exception as e:
            self.logger.error(f"发送企业微信消息出错: {e}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
