import rclpy
from rclpy.node import Node
import cv2
import traceback
import glob
import subprocess

from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class FaceCameraNode(Node):

    def __init__(self):
        super().__init__("face_camera_node")

        try:
            self.bridge = CvBridge()
            self.cap = None

            self.pub_image = self.create_publisher(
                Image,
                "/camera/standard_image",
                10
            )

            self.get_logger().info("正在搜索 USB 摄像头...")

            # 【核心功能】动态查找摄像头
            device_path = self.find_camera_device()

            if not device_path:
                error_msg = "未找到可用的 USB 摄像头 (尝试寻找 Logitech C920 或最后一个视频设备)"
                self.get_logger().error(error_msg)
                raise RuntimeError(error_msg)

            self.get_logger().info(f"发现摄像头设备: {device_path}")
            self.get_logger().info("正在初始化摄像头...")

            # 打开摄像头 (使用 V4L2 后端以获得更好的性能)
            self.cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                self.get_logger().error(f"无法打开摄像头 {device_path}")
                raise RuntimeError(f"Failed to open camera at {device_path}")

            # 关键设置：C920 必须强制使用 MJPG 格式，否则在 USB 2.0 或带宽受限下无法达到 30fps
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)

            # 设置分辨率 1280x720
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # 设置帧率 30
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            # 验证实际生效的参数 (驱动可能会回退到支持的最大值)
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

            self.get_logger().info(f"摄像头初始化成功!")
            self.get_logger().info(f"实际参数 -> 分辨率: {actual_width}x{actual_height}, FPS: {actual_fps}, 编码: MJPG")

            # 创建定时器，0.033秒一次 (~30fps)
            self.timer = self.create_timer(0.033, self.timer_callback)
        except Exception as e:
            self.get_logger().error(f"Failed to initialize camera node: {e}")
            self.get_logger().error(traceback.format_exc())
            raise

    def find_camera_device(self):
        """
        在Linux系统上查找摄像头设备，优先寻找 Logitech C920。
        """
        return self._find_camera_linux()

    def _find_camera_linux(self):
        """
        在Linux系统上查找摄像头设备
        """
        devices = sorted(glob.glob("/dev/video[0-9]*"))

        if not devices:
            return None

        target_device = None
        fallback_device = None

        for dev in devices:
            try:
                # 使用 v4l2-ctl 获取设备信息
                # timeout=2 防止某些设备卡死
                result = subprocess.run(
                    ["v4l2-ctl", "-d", dev, "--info"],
                    capture_output=True, text=True, timeout=2
                )

                info_str = result.stdout
                self.get_logger().info(f"该摄像头设备信息为：{info_str}")
                # 检查是否包含常见的外接摄像头关键词
                if "Logitech" in info_str or "C920" in info_str or "HD Pro" in info_str or "Webcam" in info_str:
                    self.get_logger().info(f"找到目标摄像头: {dev}")
                    return dev  # 直接返回找到的第一个匹配项

                # 记录最后一个设备作为备选
                fallback_device = dev

            except Exception as e:
                self.get_logger().warn(f"检查设备 {dev} 时出错: {e}")
                continue

        # 如果没有找到明确标记为 Logitech 的设备，返回最后一个设备
        # 这通常适用于只有一个外接摄像头的情况
        if fallback_device:
            self.get_logger().warn(f"未找到明确标识的 C920，将尝试使用最后一个设备: {fallback_device}")
            return fallback_device

        return None


    def timer_callback(self):
        try:
            ret, frame = self.cap.read()

            if not ret:
                self.get_logger().warn("摄像头读取失败")
                return

            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "usb_camera"

            self.pub_image.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Error in timer callback: {e}")
            self.get_logger().error(traceback.format_exc())

    def destroy_node(self):
        try:
            if self.cap:
                self.cap.release()
        except Exception as e:
            self.get_logger().error(f"Error releasing camera: {e}")

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