"""
动作基类（规则定义）:
定义所有 Motion 的统一接口
"""

class MotionBase:
    def __init__(self):
        self.started = False
        self.finished = False

    def start(self, ctx):
        """动作开始时调用（只执行一次）"""
        self.started = True

    def update(self, ctx, dt):
        """每帧调用"""
        pass

    def stop(self, ctx):
        """动作被中断"""
        self.finished = True