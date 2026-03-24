"""
动作组合:
把多个动作拼起来
"""
import math
from .base import MotionBase
from .primitives import (
    R_SHOULDER_PITCH,
    R_SHOULDER_ROLL,
    R_ELBOW,
    R_WRIST_PITCH
)


class GreetMotion(MotionBase):
    def __init__(self, person_name="friend"):
        super().__init__()
        self.person_name = person_name
        self.phase = 0
        self.timer = 0

    def start(self, ctx):
        super().start(ctx)
        ctx.led(0, 255, 0)

    def update(self, ctx, dt):
        print("greet motion update ...")
        self.timer += dt

        # ===== 阶段0：抬手 =====
        if self.phase == 0:
            duration = 1.0
            ratio = min(self.timer / duration, 1.0)

            ctx.set_joints({
                R_SHOULDER_PITCH: -0.5 * ratio,
                R_SHOULDER_ROLL:  -0.5 * ratio,
                R_ELBOW:          -1.0 * ratio,
            })

            if ratio >= 1.0:
                self.phase = 1
                self.timer = 0
                ctx.speak(f"Hello {self.person_name}!")

        # ===== 阶段1：挥手 =====
        elif self.phase == 1:
            t = self.timer

            angle = 0.8 * math.sin(2 * math.pi * 1.5 * t)

            ctx.set_joint(R_WRIST_PITCH, angle)

            if t > 3.0:
                self.phase = 2
                self.timer = 0

        # ===== 阶段2：放下手 =====
        elif self.phase == 2:
            duration = 1.0
            ratio = min(self.timer / duration, 1.0)

            ctx.set_joints({
                R_SHOULDER_PITCH: -0.5 * (1 - ratio),
                R_SHOULDER_ROLL:  -0.5 * (1 - ratio),
                R_ELBOW:          -1.0 * (1 - ratio),
            })

            if ratio >= 1.0:
                ctx.led(0, 0, 0)
                self.finished = True
