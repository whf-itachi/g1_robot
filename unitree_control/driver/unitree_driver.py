import threading
import logging

from unitree_sdk2py.core.channel import (
    ChannelFactoryInitialize,
    ChannelPublisher,
    ChannelSubscriber,
)

from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient

from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_

from unitree_sdk2py.utils.crc import CRC

# 获取logger实例
logger = logging.getLogger(__name__)


class UnitreeDriver:

    def __init__(self):
        logger.info("Initializing Unitree SDK...")

        ChannelFactoryInitialize(0, "eth0")

        # ===== locomotion =====
        self.loco = LocoClient()
        self.loco.SetTimeout(10.0)
        self.loco.Init()

        # ===== audio =====
        self.audio = AudioClient()
        self.audio.Init()
        self.audio.SetTimeout(10.0)
        self.audio.SetVolume(80)

        # ==================================================
        # ✅ 新增：低层控制（关键）
        # ==================================================

        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state = None
        self.crc = CRC()

        # 发布 / 订阅
        self.lowcmd_pub = ChannelPublisher("rt/lowcmd", LowCmd_)
        self.lowcmd_pub.Init()

        self.lowstate_sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_sub.Init(self._lowstate_handler, 10)

        # 控制线程
        self.running = True
        self.control_dt = 0.02  # 50Hz

        self.control_thread = threading.Thread(target=self._control_loop)
        self.control_thread.daemon = True
        self.control_thread.start()

        # 设置关节默认控制参数（非常重要❗）
        self._init_motors()

        logger.info("✅ UnitreeDriver initialized")

    # ==================================================
    # ✅ 低层控制核心
    # ==================================================

    def _init_motors(self):
        """初始化电机参数"""
        for i in range(len(self.low_cmd.motor_cmd)):
            self.low_cmd.motor_cmd[i].mode = 1
            self.low_cmd.motor_cmd[i].kp = 100.0
            self.low_cmd.motor_cmd[i].kd = 3.0
            self.low_cmd.motor_cmd[i].tau = 0.0

    def _lowstate_handler(self, msg: LowState_):
        self.low_state = msg

    def _control_loop(self):
        """50Hz 控制循环"""
        while self.running:
            self.low_cmd.crc = self.crc.Crc(self.low_cmd)
            self.lowcmd_pub.Write(self.low_cmd)

            import time
            time.sleep(self.control_dt)

    # ==================================================
    # locomotion
    # ==================================================

    def move(self, vx, vy, yaw):
        self.loco.Move(vx, vy, yaw)

    def stop(self):
        self.loco.StopMove()

    def stand(self):
        self.loco.HighStand()

    def sit(self):
        self.loco.Sit()

    def shake_hand(self):
        self.loco.ShakeHand()

    # ==================================================
    # audio
    # ==================================================

    def speak(self, text, volume=80):
        self.audio.SetVolume(volume)
        self.audio.TtsMaker(text, 1)

    def led(self, r, g, b):
        self.audio.LedControl(r, g, b)

    # ==================================================
    # ✅ 关节控制（你需要的）
    # ==================================================

    def set_joint(self, joint_id, q):
        self.low_cmd.motor_cmd[joint_id].q = q

    def set_joints(self, joints_dict):
        for jid, q in joints_dict.items():
            self.low_cmd.motor_cmd[jid].q = q

    # ==================================================
    # 关闭
    # ==================================================

    def close(self):
        self.running = False
        self.control_thread.join()