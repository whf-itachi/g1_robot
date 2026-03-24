"""
动作组合:
把多个动作拼起来
"""
from .base import MotionBase


# Spin动作
class SpinMotion(MotionBase):

    def __init__(self, speed=1.0, duration=3.0):
        super().__init__()
        self.speed = speed
        self.duration = duration
        self.elapsed = 0.0

    def start(self, ctx):
        super().start(ctx)
        ctx.move(0, 0, self.speed)

    def update(self, ctx, dt):
        self.elapsed += dt

        if self.elapsed >= self.duration:
            ctx.stop()
            self.finished = True


# Wave 动作
class WaveMotion(MotionBase):

    def __init__(self):
        super().__init__()
        self.phase = 0
        self.timer = 0

    def update(self, ctx, dt):
        self.timer += dt

        if self.phase == 0:
            ctx.move(0, 0, 0.5)
            if self.timer > 0.3:
                self.phase = 1
                self.timer = 0

        elif self.phase == 1:
            ctx.move(0, 0, -0.5)
            if self.timer > 0.3:
                self.phase = 0
                self.timer = 0

        # 循环3次结束
        # 你可以加计数器