"""
接收人脸识别结果，分发到不同处理器进行处理（如打招呼、企业微信通知等）
"""
import rclpy
from rclpy.node import Node

from g1_interfaces.msg import FaceResult
from sensor_msgs.msg import Image
from .face_result_handlers import FaceResultProcessor, GreetingHandler, WeChatWorkApiRequestHandler


class FaceBehaviorNode(Node):

    def __init__(self):
        super().__init__("face_behavior_node")
        
        # 创建人脸识别结果处理器
        self.processor = FaceResultProcessor()
        
        # 注册打招呼处理器
        greeting_handler = GreetingHandler(self)
        self.processor.register_handler("greeting", greeting_handler)
        
        # 注册企业微信API请求处理器
        # wechat_api_handler = WeChatWorkApiRequestHandler(self)
        # self.processor.register_handler("wechat_api_request", wechat_api_handler)

        try:
            self.face_sub = self.create_subscription(
                FaceResult,
                "/face/result",
                self.face_callback,
                10
            )
            self.get_logger().info("Face result subscriber created successfully")
            
            # 订阅图像话题，用于获取人脸识别的图像
            self.image_sub = self.create_subscription(
                Image,
                "/camera/standard_image",  # 假设这是图像话题
                self.image_callback,
                10
            )
            self.get_logger().info("Image subscriber created successfully")
        except Exception as e:
            self.get_logger().error(f"Failed to create subscription: {e}")
            raise

    def image_callback(self, msg):
        """
        图像回调函数，缓存最新图像
        """
        # 更新企业微信处理器中的图像缓存
        wechat_handler = self.processor.get_handler("wechat_api_request")
        if wechat_handler:
            wechat_handler.update_latest_image(msg)

    def face_callback(self, msg):
        """
        人脸识别结果回调函数，将结果分发给所有注册的处理器
        """
        self.get_logger().info(f"Received face result: {msg.name} with similarity {msg.similarity}")

        # 将人脸识别结果分发给所有处理器
        self.get_logger().info(f"[DEBUG] About to process face result with processor")
        self.processor.process(msg)
        self.get_logger().info(f"[DEBUG] Face result processing completed")


def main(args=None):
    rclpy.init(args=args)
    node = FaceBehaviorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
