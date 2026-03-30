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


class GreetMotion(MotionBase):
    def __init__(self, person_name="friend"):
        super().__init__()
        self.person_name = person_name
        self.phase = 0  # 0: 设置LED, 1: 说话+挥手, 2: 关闭LED
        self.timer = 0
        self.has_started_speaking = False
        self.has_started_shakehand = False

    def start(self, ctx):
        super().start(ctx)
        # 开始第一阶段：设置LED为绿色
        ctx.led(0, 255, 0)

    def update(self, ctx, dt):
        self.timer += dt

        if self.phase == 0:
            # 第0阶段：LED已设置，等待短暂时间后同时开始说话和挥手
            if self.timer > 0.3:  # 等待0.3秒
                self.phase = 1
                self.timer = 0
                # 同时开始说话和挥手
                # ctx.speak(f"Hello {self.person_name}!")
                # ctx.shake_hand()
                ctx.face_wave()
                self.has_started_speaking = True
                self.has_started_shakehand = True
                
        elif self.phase == 1:
            # 第1阶段：同时进行说话和挥手，持续一段时间
            if self.timer > 3.0:  # 语音和挥手持续3秒
                self.phase = 2
                self.timer = 0
                # 关闭LED
                ctx.led(0, 0, 0)
                
        elif self.phase == 2:
            # 最后阶段：完成所有动作
            self.finished = True
