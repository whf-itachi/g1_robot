"""动作拆解
动作原语（底层工具箱）:
把动作变成“机器人能执行的最小操作”
"""
class MotionPrimitives:

    def __init__(self, driver):
        self.d = driver

    def move(self, vx, vy, yaw):
        self.d.move(vx, vy, yaw)

    def stop(self):
        self.d.stop()

    def stand(self):
        self.d.stand()

    def sit(self):
        self.d.sit()

    def shake_hand(self):
        self.d.shake_hand()

    def led(self, r, g, b):
        self.d.led(r, g, b)