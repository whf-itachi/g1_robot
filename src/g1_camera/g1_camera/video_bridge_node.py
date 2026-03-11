import rclpy
from rclpy.node import Node

import cv2
import numpy as np

from unitree_go.msg import Go2FrontVideoData
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class VideoBridgeNode(Node):

    def __init__(self):

        super().__init__("video_bridge_node")

        self.bridge = CvBridge()

        self.sub = self.create_subscription(
            Go2FrontVideoData,
            "/frontvideostream",
            self.callback,
            10
        )

        self.pub = self.create_publisher(
            Image,
            "/camera/image",
            10
        )

        self.get_logger().info("Video bridge node started")

    def callback(self, msg):

        np_arr = np.frombuffer(msg.data, np.uint8)

        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return

        ros_image = self.bridge.cv2_to_imgmsg(frame, "bgr8")

        self.pub.publish(ros_image)

        # 调试显示
        cv2.imshow("robot_camera", frame)
        cv2.waitKey(1)


def main():

    rclpy.init()

    node = VideoBridgeNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()