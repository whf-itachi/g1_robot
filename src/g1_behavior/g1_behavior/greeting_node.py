import rclpy
from rclpy.node import Node

import time
from threading import Thread

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from g1_interfaces.msg import FaceResult
from g1_interfaces.msg import MotionCmd


class GreetingNode(Node):

    def __init__(self):
        super().__init__("greeting_node")
        ChannelFactoryInitialize(0)  # 初始化DDS通信通道
        self.get_logger().info("Greeting node started")

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

        # 发布动作
        self.motion_pub = self.create_publisher(
            MotionCmd,
            "/motion/cmd",
            10
        )

    def face_callback(self, msg):
        # 如果正在打招呼 忽略
        if self.robot_state == "GREETING":
            self.get_logger().info(
                f"Robot greeting, ignore!"
            )
            return

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

        self.get_logger().info(
            f"Face detected: {name}"
        )
        # self.handle_greeting(name) 改为使用线程 避免阻塞ROS回调导致 rclpy.spin 无法处理其他消息
        Thread(target=self.handle_greeting, args=(name,)).start()

    def handle_greeting(self, name):
        # 执行打招呼
        self.robot_state = "GREETING"
        self.say_hello(name)

        cmd = MotionCmd()
        cmd.cmd = "wave_hand"
        cmd.param = name
        self.motion_pub.publish(cmd)

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