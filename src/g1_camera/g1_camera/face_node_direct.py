import rclpy
from rclpy.node import Node
import cv2

from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class FaceCameraNode(Node):

    def __init__(self):
        super().__init__("face_camera_node")

        self.bridge = CvBridge()

        # 发布图像
        self.pub_image = self.create_publisher(Image, "/camera/standard_image", 10)

        # USB 摄像头
        device = "/dev/video0"

        self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            self.get_logger().error(f"无法打开摄像头 {device}")
            return

        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.get_logger().info(f"USB 摄像头 {device} 初始化成功")

        # 10Hz 发布
        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):

        ret, frame = self.cap.read()

        if not ret:
            self.get_logger().warn("读取摄像头失败")
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "usb_camera"

        self.pub_image.publish(msg)

    def destroy_node(self):

        if self.cap:
            self.cap.release()

        super().destroy_node()


def main(args=None):

    rclpy.init(args=args)

    node = FaceCameraNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()