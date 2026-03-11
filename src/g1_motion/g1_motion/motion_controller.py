import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


class MotionController:

    def __init__(self):

        ChannelFactoryInitialize(0)
        self.motion = LocoClient()

        self.motion.Init()

        self.state = "IDLE"

    def init(self):
        pass

    def stop(self):

        if self.state == "STOPPING":
            return

        print("Stopping robot...")

        self.state = "STOPPING"

        self.motion.StopMove()

        time.sleep(1.5)

        self.state = "IDLE"

    def wave_hand(self):

        if self.is_moving():
            self.stop()

        print("Robot waving hand")

        self.state = "GREETING"

        self.motion.WaveHand()

        time.sleep(1.0)

        self.state = "IDLE"

    def is_moving(self):
        return self.state == "MOVING"

    def set_moving(self, moving: bool):

        if moving:
            self.state = "MOVING"
        else:
            self.state = "IDLE"

    def is_busy(self):
        return self.state in ["STOPPING", "GREETING", "MOVING"]