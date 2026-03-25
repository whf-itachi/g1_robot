"""
executor.py
调度器：控制动作的生命周期
"""
import time


class MotionExecutor:

    def __init__(self, primitives):
        self.primitives = primitives
        self.current_motion = None
        self.last_time = time.time()
        self.running = True

    def execute(self, motion):
        """执行新动作（会打断当前动作）"""
        if self.current_motion:
            self.current_motion.stop(self.primitives)

        self.current_motion = motion
        self.current_motion.started = False

    def stop(self):
        """强制停止"""
        if self.current_motion:
            self.current_motion.stop(self.primitives)
            self.current_motion = None

        self.primitives.stop()

    def update(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        if not self.current_motion:
            return

        motion = self.current_motion

        if not motion.started:
            motion.start(self.primitives)

        motion.update(self.primitives, dt)

        # 每帧下发
        self.primitives.apply()

        if motion.finished:
            self.current_motion = None