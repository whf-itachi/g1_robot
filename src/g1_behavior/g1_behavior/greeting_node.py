import rclpy
from rclpy.node import Node

import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from g1_interfaces.msg import FaceResult
from g1_motion.motion_node import MotionController


class GreetingNode(Node):

    def __init__(self):
        super().__init__("greeting_node")
        ChannelFactoryInitialize(0)
        self.get_logger().info("Greeting node started")
        # 动作控制器
        self.motion = MotionController()
        self.motion.init()
        # 一分钟去重
        self.last_seen = {}
        # 当前机器人状态
        self.robot_state = "IDLE"
        self.sub = self.create_subscription(
            FaceResult,
            "/face/result",
            self.face_callback,
            10
        )

    def face_callback(self, msg):
        name = msg.name
        similarity = msg.similarity
        now = time.time()
        # 相似度过滤
        if similarity < 0.6:
            return
        # 一分钟内不重复
        if name in self.last_seen:
            if now - self.last_seen[name] < 60:
                return
        self.last_seen[name] = now
        # 如果正在打招呼 忽略
        if self.robot_state == "GREETING":

            self.get_logger().info(
                f"Robot greeting, ignore {name}"
            )
            return
        self.get_logger().info(
            f"Face detected: {name}"
        )
        self.handle_greeting(name)

    def handle_greeting(self, name):
        # 如果机器人在移动
        if self.motion.is_moving():
            self.get_logger().info(
                "Robot moving, stopping first"
            )
            self.robot_state = "STOPPING"
            self.motion.stop()
        # 等待完全停止
        time.sleep(0.5)
        # 执行打招呼
        self.robot_state = "GREETING"
        self.say_hello(name)
        self.motion.wave_hand()
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