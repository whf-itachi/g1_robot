import time

from unitree_sdk2py.g1.motion.g1_motion_client import MotionClient


class MotionController:

    def __init__(self):

        self.motion = MotionClient()

        self.motion.Init()

        self.state = "IDLE"

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

        self.motion.PlayMotion(
            "wave_hand",
            wait_finish=True
        )

        self.state = "IDLE"

    def is_moving(self):

        return self.state == "MOVING"

    def is_busy(self):

        return self.state in ["STOPPING", "GREETING"]