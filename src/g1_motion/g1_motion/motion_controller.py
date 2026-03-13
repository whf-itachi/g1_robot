import time
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


class MotionController:

    def __init__(self):
        self.motion = LocoClient()
        self.motion.Init()
        self.state = "IDLE"
        self.motion.WaitLeaseApplied()
        self.motion.Start()
        self.motion.HighStand()

    def init(self):
        pass

    def stop(self):

        if self.state == "STOPPING":
            return

        print("Stopping robot...")
        self.state = "STOPPING"
        self.motion.StopMove()
        self.state = "IDLE"

    def wave_hand(self):
        if self.state == "GREETING":
            return  # 避免重入

        if self.is_moving():
            self.stop()

        print("Robot waving hand")
        self.state = "GREETING"
        # self.motion.WaveHand()
        self.motion.ShakeHand()
        time.sleep(1.0)
        self.motion.HighStand()
        self.state = "IDLE"

    def is_moving(self):
        # 判断当前机器人状态并返回是否处于动作执行中todo

        return self.state == "MOVING"

    def set_moving(self, moving: bool):
        if moving:
            self.state = "MOVING"
        else:
            self.state = "IDLE"

    def is_busy(self):
        return self.state in ["STOPPING", "GREETING", "MOVING"]