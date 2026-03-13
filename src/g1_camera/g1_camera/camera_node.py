import rclpy
from rclpy.node import Node
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from unitree_go.msg import Go2FrontVideoData


class G1CameraDecoder(Node):
    def __init__(self):
        super().__init__("g1_camera_decoder")
        self.bridge = CvBridge()
        # 订阅机器人发出的压缩流
        self.sub = self.create_subscription(
            Go2FrontVideoData, "/frontvideostream", self.callback, 10)
        # 发布给 face_node 使用的标准图片
        self.pub = self.create_publisher(Image, "old/camera", 10)  # 该文件暂时保留添加old头进行区别
        self.get_logger().info("解码中转站已启动...")

    def callback(self, msg):
        try:
            # 关键：将 bytes 转换为 numpy 数组
            data = np.frombuffer(bytes(msg.video_data), dtype=np.uint8)
            # 使用 cv2 解码。宇树的流通常是 JPEG 压缩
            frame = cv2.imdecode(data, cv2.IMREAD_COLOR)

            if frame is not None:
                # 成功解码，发布标准 ROS2 图片
                ros_img = self.bridge.cv2_to_imgmsg(frame, "bgr8")
                self.pub.publish(ros_img)
            else:
                # 如果解码失败，静默处理，不要打印报错
                pass
        except Exception:
            pass


def main(args=None):
    # 1. 初始化 rclpy 环境
    rclpy.init(args=args)

    # 2. 实例化你的节点
    node = G1CameraDecoder()

    try:
        # 3. 开启循环监听，处理回调函数
        rclpy.spin(node)
    except KeyboardInterrupt:
        # 4. 捕获 Ctrl+C，优雅退出
        node.get_logger().info("正在停止 G1 相机解码节点...")
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        # 5. 确保销毁节点和关闭环境（释放内存和话题句柄）
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()