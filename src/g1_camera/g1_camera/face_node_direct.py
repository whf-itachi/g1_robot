import rclpy
from rclpy.node import Node
import cv2

from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class FaceCameraNode(Node):

    def __init__(self):
        super().__init__("face_camera_node")

        self.bridge = CvBridge()

        self.pub_image = self.create_publisher(
            Image,
            "/camera/standard_image",
            10
        )

        # 打开摄像头（C920 推荐写法）
        self.cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)

        if not self.cap.isOpened():
            self.get_logger().error("无法打开摄像头 /dev/video0")
            return

        # C920 必须设置 MJPG
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # 设置帧率
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.get_logger().info("USB 摄像头初始化成功")

        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):

        ret, frame = self.cap.read()

        if not ret:
            self.get_logger().warn("摄像头读取失败")
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