"""
primitives.py
动作拆解,动作原语（底层工具箱）:
把动作变成"机器人能执行的最小操作"
"""
# ===== G1 右臂关节 =====
R_SHOULDER_PITCH = 22
R_SHOULDER_ROLL = 23
R_SHOULDER_YAW = 24
R_ELBOW = 25
R_WRIST_ROLL = 26
R_WRIST_PITCH = 27
R_WRIST_YAW = 28


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

    def speak(self, text, volume=80):
        self.d.speak(text, volume)

    # ===== 新增：关节控制 =====
    def set_joint(self, joint_id, q):
        self.d.set_joint(joint_id, q)

    def set_joints(self, joints_dict):
        self.d.set_joints(joints_dict)