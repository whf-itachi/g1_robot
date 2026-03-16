import rclpy
from rclpy.node import Node

from threading import Thread, Lock

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from g1_interfaces.msg import FaceResult
from g1_interfaces.msg import MotionCmd


class GreetingNode(Node):

    def __init__(self):
        super().__init__("greeting_node")
        
        try:
            ChannelFactoryInitialize(0)  # 初始化 DDS 通信通道
            self.get_logger().info("Greeting node started")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize DDS communication channel: {e}")
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

        try:
            self.sub = self.create_subscription(
                FaceResult,
                "/face/result",
                self.face_callback,
                10
            )

            # 发布动作
            self.motion_pub = self.create_publisher(
                MotionCmd,
                "/motion/cmd",
                10
            )
        except Exception as e:
            self.get_logger().error(f"Failed to create subscriptions/publishers: {e}")
            raise

    def face_callback(self, msg):
        # 获取当前机器人状态
        with self.state_lock:
            current_state = self.robot_state
            
        # 如果正在打招呼 忽略
        if current_state == "GREETING":
            self.get_logger().info(
                f"Robot greeting, ignore!"
            )
            return

        name = msg.name
        similarity = msg.similarity
        # 相似度过滤
        if similarity < 0.6:
            return

        # 使用 ROS2 时钟进行去重检查
        now = self.get_clock().now().nanoseconds / 1e9
        with self.seen_lock:
            if name in self.last_seen:
                if now - self.last_seen[name] < self.dedup_interval:
                    return
            self.last_seen[name] = now

        self.get_logger().info(
            f"Face detected: {name}"
        )
        # 使用线程 避免阻塞 ROS 回调导致 rclpy.spin 无法处理其他消息
        Thread(target=self.handle_greeting, args=(name,), daemon=True).start()

    def handle_greeting(self, name):
        # 执行打招呼
        with self.state_lock:
            self.robot_state = "GREETING"
        
        self.say_hello(name)

        cmd = MotionCmd()
        cmd.cmd = "wave_hand"
        cmd.param = name
        
        try:
            self.motion_pub.publish(cmd)
        except Exception as e:
            self.get_logger().error(f"Failed to publish motion command: {e}")

        with self.state_lock:
            self.robot_state = "IDLE"
            
        self.get_logger().info(
            f"Greeting finished: {name}"
        )

    def say_hello(self, name):
        text = f"Hello {name}"
        self.get_logger().info(text)


def main(args=None):
    rclpy.init(args=args)
    node = GreetingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
