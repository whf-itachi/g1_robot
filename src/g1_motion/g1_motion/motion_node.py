import rclpy
from rclpy.node import Node

from .motion_controller import MotionController


class MotionNode(Node):

    def __init__(self):

        super().__init__("motion_node")

        self.controller = MotionController()

        self.get_logger().info("Motion node started")


def main(args=None):

    rclpy.init(args=args)

    node = MotionNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()