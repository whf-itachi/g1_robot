import rclpy
from rclpy.node import Node
import cv2
import numpy as np
import os
import insightface

# 宇树 SDK2 官方推荐的视频导入方式
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient

# 你的业务逻辑导入
from g1_interfaces.msg import FaceResult
from g1_face.face_database import FaceDatabase


class FaceNodeDirect(Node):
    def __init__(self):
        super().__init__("face_node_direct")

        # 1. 初始化 SDK 通道
        ChannelFactoryInitialize(0)

        # 2. 使用官方 VideoClient (这是 G1/Go2 的标准做法)
        self.client = VideoClient()
        self.client.Init()

        # 创建一个定时器来轮询视频帧 (VideoClient 通常使用拉取模式)
        self.timer = self.create_timer(0.03, self.process_video_frame)  # 约 30fps

        # 3. 初始化人脸识别
        self.detector = insightface.app.FaceAnalysis(
            model='buffalo_l', providers=['CPUExecutionProvider'])
        self.detector.prepare(ctx_id=0)

        db_path = os.path.expanduser("~/haitch/g1_robot/data/face_database.json")
        self.db = FaceDatabase(db_path)

        # 4. 初始化 ROS2 发布者
        self.pub = self.create_publisher(FaceResult, "/face/result", 10)
        self.get_logger().info(f"✅ G1 人脸识别直连节点已启动")

    def process_video_frame(self):
        # 从 VideoClient 获取最新图像
        # code, data = self.client.GetImage()
        code, data = self.client.GetImageSample()
        if code != 0:
            # code 0 表示成功，如果不为 0 可能还没收到数据，跳过即可
            return

        try:
            # 解码图像数据
            img_array = np.frombuffer(bytes(data), np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is not None:
                # 执行识别
                faces = self.detector.get(frame)
                for face in faces:
                    name, sim = self.db.match(face.embedding)

                    if name:
                        self.get_logger().info(f"👤 检测到: {name} (相似度: {sim:.2f})")
                        result = FaceResult()
                        result.name = name
                        result.similarity = float(sim)
                        self.pub.publish(result)

                # 调试窗口（可选）
                # cv2.imshow("G1 Face Detection", frame)
                # cv2.waitKey(1)

        except Exception as e:
            self.get_logger().error(f"处理视频帧时出错: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = FaceNodeDirect()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()