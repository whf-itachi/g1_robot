"""
接收运动命令并控制G1机器人执行相应的动作（如挥手、停止等）
"""
import rclpy
from rclpy.node import Node
import traceback

from unitree_sdk2py.core.channel import ChannelFactoryInitialize

from .motion_controller import MotionController
from g1_interfaces.msg import MotionCmd


class MotionNode(Node):
    def __init__(self):
        super().__init__("motion_node")

        self.get_logger().info("Initializing Unitree SDK Channel Factory...")
        try:
            ChannelFactoryInitialize(1)
            self.get_logger().info("SDK Channel Factory initialized successfully.")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize SDK: {e}")
            self.get_logger().error(traceback.format_exc())
            raise e

        self.get_logger().info("Creating MotionController...")
        try:
            self.controller = MotionController()
            self.get_logger().info("MotionController created and ready.")
        except Exception as e:
            self.get_logger().error(f"Failed to create MotionController: {e}")
            self.get_logger().error(traceback.format_exc())
            raise e

        try:
            self.sub = self.create_subscription(
                MotionCmd,
                "/motion/cmd",
                self.cmd_callback,
                10
            )
            self.get_logger().info("MotionNode subscription created successfully.")
        except Exception as e:
            self.get_logger().error(f"Failed to create motion command subscription: {e}")
            raise e


    def cmd_callback(self, msg):
        try:
            self.get_logger().info(f"Motion cmd received: {msg.cmd}, param: {msg.param}")
            if msg.cmd == "wave_hand":
                self.get_logger().info("Robot wave hand")
                self.get_logger().info(f"[DEBUG] About to call controller.wave_hand() for param: {msg.param}")
                self.controller.wave_hand()
                self.get_logger().info(f"[DEBUG] controller.wave_hand() completed")

            elif msg.cmd == "natural_greeting":
                self.get_logger().info("Robot performing natural greeting")
                self.get_logger().info(f"[DEBUG] About to call controller.natural_greeting()")
                self.controller.natural_greeting()
                self.get_logger().info(f"[DEBUG] controller.natural_greeting() completed")

            elif msg.cmd == "stop":
                self.get_logger().info(f"[DEBUG] About to call controller.stop()")
                self.controller.stop()
                self.get_logger().info(f"[DEBUG] controller.stop() completed")
        except Exception as e:
            self.get_logger().error(f"Error processing motion command: {e}")
            self.get_logger().error(traceback.format_exc())


def main(args=None):
    rclpy.init(args=args)
    node = MotionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()