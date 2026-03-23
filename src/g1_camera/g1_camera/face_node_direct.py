"""
从外部摄像头源（如USB摄像头）接收图像并转发到人脸识别系统
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

# 导入日志配置
from common.logger_config import get_logger


class FaceCameraNode(Node):
    def __init__(self):
        super().__init__("face_camera_node")

        # 使用自定义日志记录器
        self.logger = get_logger(self.get_name())

        self.bridge = CvBridge()

        # 发布最终图像
        self.pub_image = self.create_publisher(Image, "/camera/standard_image", 30)

        # 订阅另一个工作空间的图像
        self.sub = self.create_subscription(
            Image,
            "/c920/image_raw",
            self.callback,
            30  # 队列放大，防止YUYV丢包
        )

        self.logger.info("已订阅 /c920/image_raw (只使用ROS2通信，不占用摄像头)")

    def callback(self, msg):
        try:
            # 更新时间戳和frame_id
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "camera"

            # 发布图像
            self.pub_image.publish(msg)
        except Exception as e:
            self.logger.error(f"发布图像时发生错误: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = FaceCameraNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.logger.info("节点被用户中断")
    except Exception as e:
        node.logger.error(f"运行过程中出现异常: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()