import rclpy
from rclpy.node import Node

import insightface
import numpy as np

from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from g1_interfaces.msg import FaceResult
from .face_database import FaceDatabase


class FaceNode(Node):

    def __init__(self):

        super().__init__("face_node")

        self.bridge = CvBridge()

        self.detector = insightface.app.FaceAnalysis(
            model='buffalo_l',
            providers=['CPUExecutionProvider']
        )

        self.detector.prepare(ctx_id=0)

        self.db = FaceDatabase(
            "/home/haitch/haitch/g1_robot/data/face_database.json"
        )

        self.sub = self.create_subscription(
            Image,
            "/camera/image",
            self.callback,
            10
        )

        self.pub = self.create_publisher(
            FaceResult,
            "/face/result",
            10
        )

    def callback(self, msg):

        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")

        faces = self.detector.get(frame)

        for face in faces:

            name, sim = self.db.match(face.embedding)

            if name:

                result = FaceResult()

                result.name = name
                result.similarity = sim

                self.pub.publish(result)


def main():

    rclpy.init()

    node = FaceNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()
