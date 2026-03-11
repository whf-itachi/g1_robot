import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


class MotionController:

    def __init__(self):
        if not hasattr(MotionController, "_initialized"):
            ChannelFactoryInitialize(0)
            MotionController._initialized = True

        self.motion = LocoClient()

        self.state = "IDLE"

    def init(self):
        """初始化运动控制器"""
        if self.state == "IDLE":
            self.motion.Init()

    def stop(self):

        if self.state == "STOPPING":
            return

        print("Stopping robot...")

        self.state = "STOPPING"

        self.motion.StopMove()

        time.sleep(1.5)

        self.state = "IDLE"

    def wave_hand(self):

        print("Robot waving hand")

        self.state = "GREETING"

        self.motion.WaveHand()

        time.sleep(1.0)

        self.state = "IDLE"

    def is_moving(self):
        """检查机器人是否正在移动"""
        return self.state == "MOVING"

    def set_moving(self, is_moving: bool):
        """设置移动状态"""
        self.state = "MOVING" if is_moving else "IDLE"

    def is_busy(self):

        return self.state in ["STOPPING", "GREETING", "MOVING"]


def main(args=None):
    import rclpy
    rclpy.init(args=args)

    node = MotionController()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()
