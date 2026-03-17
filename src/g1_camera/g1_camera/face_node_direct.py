import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class FaceCameraNode(Node):
    def __init__(self):
        super().__init__("face_camera_node")

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

        self.get_logger().info("✅ 已订阅 /c920/image_raw (只使用ROS2通信，不占用摄像头)")

    def callback(self, msg):
        # 只要进来这里，就说明通信成功！
        self.get_logger().info(f"📸 收到图像：{msg.width}x{msg.height}")

        # 直接转发
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera"
        self.pub_image.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = FaceCameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()