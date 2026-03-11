import rclpy
from rclpy.node import Node
import cv2
import numpy as np

# 关键修改：导入宇树自定义消息类型
# 请确保已 source 了包含 unitree_go 的工作空间
try:
    from unitree_go.msg import Go2FrontVideoData
except ImportError:
    print("错误：找不到 unitree_go 消息定义。请先执行 source 宇树工作空间/setup.bash")


class G1CameraNode(Node):
    def __init__(self):
        super().__init__("g1_camera_node")

        # 修改点 1：订阅话题改为机器人现有的视频流话题
        self.subscription = self.create_subscription(
            Go2FrontVideoData,
            "/frontvideostream",
            self.image_callback,
            10
        )

        self.get_logger().info("已连接到 G1 机器人内置视频流 (/frontvideostream)")

    def image_callback(self, msg):
        try:
            # 修改点 2：将压缩的字节流转换为 OpenCV 格式
            # msg.video_data 是原始字节数据，我们需要先转为 numpy 数组
            np_arr = np.frombuffer(bytes(msg.video_data), np.uint8)

            # 使用 cv2.imdecode 进行解码
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                # 显示图像
                cv2.imshow("G1 Real-time Video", frame)
                cv2.waitKey(1)
            else:
                self.get_logger().warn("接收到数据但解码失败")

        except Exception as e:
            self.get_logger().error(f"处理视频流出错: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = G1CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()