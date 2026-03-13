import rclpy
from rclpy.node import Node
import cv2
import numpy as np

# 宇树 SDK
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient

# ROS 消息
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class FaceNodeMultiSource(Node):
    def __init__(self):
        super().__init__("face_node_multi_source")

        self.bridge = CvBridge()

        # --- 发布者：发布原始图像 (注意话题名和类型) ---
        # 下游节点将订阅这个话题
        self.pub_image = self.create_publisher(Image, "/camera/standard_image", 10)

        # --- 1. 初始化宇树 SDK ---
        self.unitree_client = None
        try:
            ChannelFactoryInitialize(0)
            self.unitree_client = VideoClient()
            self.unitree_client.Init()
            self.get_logger().info("✅ 宇树 VideoClient 初始化成功")
            # 频率 10Hz 足够用于识别，降低 CPU 占用
            self.timer_unitree = self.create_timer(0.1, self.callback_unitree_video)
        except Exception as e:
            self.get_logger().error(f"❌ 宇树 SDK 初始化失败: {e}")
            self.timer_unitree = None

        # --- 2. 初始化 USB 摄像头 ---
        self.usb_cap = None
        usb_device = "/dev/video0"
        try:
            self.usb_cap = cv2.VideoCapture(usb_device)
            if not self.usb_cap.isOpened():
                raise IOError(f"无法打开设备 {usb_device}")
            self.usb_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.usb_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.get_logger().info(f"✅ USB 摄像头 ({usb_device}) 初始化成功")
            self.timer_usb = self.create_timer(0.1, self.callback_usb_video)
        except Exception as e:
            self.get_logger().error(f"❌ USB 摄像头初始化失败: {e}")
            self.timer_usb = None

    def callback_unitree_video(self):
        if not self.unitree_client: return
        code, data = self.unitree_client.GetImageSample()
        if code == 0 and data:
            try:
                img_array = np.frombuffer(bytes(data), np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if frame is not None:
                    self.publish_frame(frame, "UnitreeCam")
            except:
                pass
        else:
            self.get_logger().error(f"G1 摄像头获取数据失败！")

    def callback_usb_video(self):
        if not self.usb_cap or not self.usb_cap.isOpened(): return
        ret, frame = self.usb_cap.read()
        if ret and frame is not None:
            self.publish_frame(frame, "USBCam")

    def publish_frame(self, frame, source_name):
        # 核心改动：不再做识别，直接转成 ROS Image 消息发布
        # 注意：CvBridge 需要知道编码，通常是 bgr8
        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = source_name  # 用 frame_id 标记来源
        self.pub_image.publish(msg)

    def destroy_node(self):
        if self.usb_cap: self.usb_cap.release()
        self.unitree_client = None
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FaceNodeMultiSource()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()