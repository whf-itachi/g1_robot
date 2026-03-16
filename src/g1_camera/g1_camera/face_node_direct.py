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
            
            # 定义输出主题
            self.pub_image = self.create_publisher(
                Image,
                "/camera/standard_image",
                10
            )
            
            # 尝试订阅v4l2_camera_node发布的图像数据
            self.v4l2_sub = self.create_subscription(
                Image,
                "/c920/image_raw",  # 根据启动命令，v4l2_camera_node输出主题
                self.v4l2_image_callback,
                10
            )
            
            # 添加一个标志来跟踪是否收到了来自v4l2节点的数据
            self.v4l2_available = False
            self.last_v4l2_time = self.get_clock().now()
            
            # 设置超时时间（秒），如果超过此时间没有收到v4l2数据，则启用本地摄像头
            self.v4l2_timeout = 5.0  # 5秒超时
            
            self.get_logger().info("正在等待 v4l2_camera_node 数据...")

            # 启动定时器来检查v4l2数据是否可用
            self.check_timer = self.create_timer(1.0, self.check_v4l2_availability)
            
            # 初始化本地摄像头（备用方案）
            self.initialize_local_camera()
            
        except Exception as e:
            self.get_logger().error(f"Failed to initialize camera node: {e}")
            self.get_logger().error(traceback.format_exc())
            raise

    def v4l2_image_callback(self, msg):
        """处理来自v4l2_camera_node的图像数据"""
        try:
            # 更新最后接收时间
            self.last_v4l2_time = self.get_clock().now()
            was_available = self.v4l2_available
            self.v4l2_available = True
            
            # 如果之前不可用，现在变为可用，则禁用本地摄像头定时器
            if not was_available and self.v4l2_available and hasattr(self, 'timer') and self.timer:
                self.timer.cancel()
            
            # 确保消息符合标准格式
            # 更新时间戳以确保实时性
            msg.header.stamp = self.get_clock().now().to_msg()
            # 统一frame_id
            msg.header.frame_id = "camera"
            
            # 直接转发图像消息
            self.pub_image.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Error processing v4l2 image: {e}")
            self.get_logger().error(traceback.format_exc())

    def check_v4l2_availability(self):
        """检查v4l2数据是否可用，如果超时则启用本地摄像头"""
        current_time = self.get_clock().now()
        time_since_last_v4l2 = (current_time - self.last_v4l2_time).nanoseconds / 1e9
        
        was_available = self.v4l2_available
        
        if time_since_last_v4l2 > self.v4l2_timeout and self.v4l2_available:
            self.get_logger().warn("v4l2_camera_node 数据超时，切换到本地摄像头")
            self.v4l2_available = False
        
        # 如果还没有初始化本地摄像头且v4l2不可用，则初始化
        if not self.v4l2_available and not self.cap:
            self.initialize_local_camera()
        
        # 如果v4l2状态发生变化（从可用变为不可用），且本地摄像头已准备好，则启用本地摄像头定时器
        if was_available and not self.v4l2_available and hasattr(self, 'timer'):
            # 重新创建定时器（如果已被取消）
            if self.timer is None or (hasattr(self.timer, 'timer_period_ns') and self.timer.timer_period_ns == 0):  # 如果定时器已被取消
                self.timer = self.create_timer(0.033, self.timer_callback)
    
    def initialize_local_camera(self):
        """初始化本地USB摄像头（备用方案）"""
        if self.cap is not None:  # 已经初始化过了
            return
            
        try:
            self.get_logger().info("正在搜索 USB 摄像头...")

            # 【核心功能】动态查找摄像头
            device_path = self.find_camera_device()

            if not device_path:
                error_msg = "未找到可用的 USB 摄像头 (尝试寻找 Logitech C920 或最后一个视频设备)"
                self.get_logger().error(error_msg)
                return  # 不抛出异常，因为还有其他数据源

            self.get_logger().info(f"发现摄像头设备: {device_path}")
            self.get_logger().info("正在初始化摄像头...")

            # 打开摄像头 (使用 V4L2 后端以获得更好的性能)
            self.cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                self.get_logger().error(f"无法打开摄像头 {device_path}")
                return  # 不抛出异常，因为还有其他数据源

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
            # 只有在v4l2不可用时才启动定时器
            if not self.v4l2_available:
                self.timer = self.create_timer(0.033, self.timer_callback)
            else:
                self.timer = None  # v4l2可用时，定时器设为None
        except Exception as e:
            self.get_logger().error(f"Failed to initialize local camera: {e}")
            self.get_logger().error(traceback.format_exc())

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
        """本地摄像头的定时回调函数"""
        try:
            # 只有在v4l2不可用时才使用本地摄像头
            if self.v4l2_available:
                return  # 如果v4l2可用，则不使用本地摄像头
                
            ret, frame = self.cap.read()

            if not ret:
                self.get_logger().warn("摄像头读取失败")
                return

            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "camera"  # 统一frame_id

            self.pub_image.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Error in timer callback: {e}")
            self.get_logger().error(traceback.format_exc())

    def destroy_node(self):
        try:
            if self.cap:
                self.cap.release()
            if hasattr(self, 'timer') and self.timer is not None:
                try:
                    self.timer.cancel()
                except:
                    pass  # 定时器可能已经被取消
            if hasattr(self, 'check_timer') and self.check_timer:
                self.check_timer.cancel()
        except Exception as e:
            self.get_logger().error(f"Error releasing resources: {e}")

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