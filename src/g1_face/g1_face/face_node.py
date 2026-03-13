import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
import os

import insightface

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

        # 使用包共享目录中的数据文件
        db_path = os.path.expanduser("~/haitch/g1_robot/data/face_database.json")
        # 如果包路径下没有，则尝试相对路径
        if not os.path.exists(db_path):
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'data', 'face_database.json'
            )

        self.db = FaceDatabase(db_path)
        self.get_logger().info(f"database size: {len(self.db.data)}")

        self.sub = self.create_subscription(
            Image,
            "/camera/standard_image",
            self.callback,
            10
        )

        self.pub = self.create_publisher(FaceResult, "/face/result", 10)
        self.get_logger().info(f"人脸识别节点就绪，数据库大小: {len(self.db.data)}")

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        faces = self.detector.get(frame)
        self.get_logger().info(f"detected faces: {len(faces)}")

        for face in faces:
            name, sim = self.db.match(face.embedding)
            self.get_logger().info(f"match result: {name}, sim={sim}")

            if name:
                result = FaceResult()
                result.name = name
                result.similarity = float(sim)
                self.pub.publish(result)


def main():
    rclpy.init()
    node = FaceNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
