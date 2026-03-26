"""
接收摄像头节点数据并进行人脸识别，将人脸识别结果进行发布到 /face/result 话题
"""
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
import os
import traceback

import insightface

from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from g1_interfaces.msg import FaceResult
from .face_database import FaceDatabase

# 导入日志配置
from common.logger_config import get_logger


class FaceNode(Node):

    def __init__(self):
        super().__init__("face_node")

        # 使用自定义日志记录器
        self.logger = get_logger(self.get_name())

        # 添加帧率控制
        self.process_every_n_frames = 5  # 每5帧处理一次，降低CPU负载
        self.frame_counter = 0

        try:
            self.bridge = CvBridge()
            self.logger.info("Initializing InsightFace detector...")
            self.detector = insightface.app.FaceAnalysis(
                model='buffalo_l',
                providers=['CPUExecutionProvider']
            )

            self.detector.prepare(ctx_id=0)
            self.logger.info("InsightFace detector initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize InsightFace detector: {e}")
            self.logger.error(traceback.format_exc())
            raise

        # 使用包共享目录中的数据文件
        try:
            package_share_dir = get_package_share_directory('g1_face')
            db_path = os.path.join(package_share_dir, 'data', 'face_database.json')
        except Exception as e:
            self.logger.error(f"Failed to get package share directory: {e}")
            raise

        try:
            self.db = FaceDatabase(db_path)
            self.logger.info(f"人脸识别节点就绪，数据库大小：{len(self.db.data)}")
        except Exception as e:
            self.logger.error(f"Failed to load face database: {e}")
            raise

        try:
            self.sub = self.create_subscription(
                Image,
                "/camera/standard_image",
                self.callback,
                10
            )

            self.pub = self.create_publisher(FaceResult, "/face/result", 10)
            self.logger.info(f"人脸识别节点就绪，数据库大小: {len(self.db.data)}, processing every {self.process_every_n_frames} frames")
        except Exception as e:
            self.logger.error(f"Failed to create subscription/publisher: {e}")
            raise

    def callback(self, msg):
        # 帧率控制：只处理每N帧中的1帧
        self.frame_counter += 1
        if self.frame_counter % self.process_every_n_frames != 0:
            return  # 跳过此帧
        
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            faces = self.detector.get(frame)
            self.logger.debug(f"detected faces: {len(faces)}")

            for face in faces:
                name, sim = self.db.match(face.embedding)
                self.logger.info(f"match result: {name}, sim={sim}")

                if name:
                    result = FaceResult()
                    result.name = name
                    result.similarity = float(sim)
                    self.pub.publish(result)
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            self.logger.error(traceback.format_exc())


def main():
    rclpy.init()
    node = FaceNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
