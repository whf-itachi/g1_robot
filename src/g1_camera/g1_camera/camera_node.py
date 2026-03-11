import rclpy
from rclpy.node import Node

import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraNode(Node):

    def __init__(self):

        super().__init__('camera_node')

        self.cap = cv2.VideoCapture(0)

        self.bridge = CvBridge()

        self.publisher = self.create_publisher(
            Image,
            "/camera/image",
            10
        )

        self.timer = self.create_timer(
            0.5,
            self.publish_frame
        )

    def publish_frame(self):

        ret, frame = self.cap.read()

        if not ret:
            return

        msg = self.bridge.cv2_to_imgmsg(frame, "bgr8")

        self.publisher.publish(msg)


def main():

    rclpy.init()

    node = CameraNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()