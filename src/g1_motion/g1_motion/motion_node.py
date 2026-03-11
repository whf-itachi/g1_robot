import rclpy
from rclpy.node import Node

from unitree_sdk2py.core.channel import ChannelFactoryInitialize

from .motion_controller import MotionController
from g1_interfaces.msg import MotionCmd


class MotionNode(Node):
    def __init__(self):
        super().__init__("motion_node")

        self.get_logger().info("Initializing Unitree SDK Channel Factory...")
        try:
            ChannelFactoryInitialize(0)
            self.get_logger().info("SDK Channel Factory initialized successfully.")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize SDK: {e}")
            raise e

        self.get_logger().info("Creating MotionController...")
        try:
            self.controller = MotionController()
            self.get_logger().info("MotionController created and ready.")
        except Exception as e:
            self.get_logger().error(f"Failed to create MotionController: {e}")
            raise e

        self.sub = self.create_subscription(
            MotionCmd,
            "/motion/cmd",
            self.cmd_callback,
            10
        )


    def cmd_callback(self, msg):
        self.get_logger().info(f"Motion cmd received: {msg.cmd}")
        if msg.cmd == "wave_hand":
            self.get_logger().info("Robot wave hand")
            self.controller.wave_hand()

        elif msg.cmd == "stop":
            self.controller.stop()


def main(args=None):
    rclpy.init(args=args)
    node = MotionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()